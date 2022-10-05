# -*- coding: utf-8 -*-
"""Functions for group management and group queries."""

__copyright__ = 'Copyright (c) 2018-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from collections import OrderedDict

import genquery
import requests

from util import *


__all__ = ['api_group_data',
           'api_group_categories',
           'api_group_subcategories',
           'api_group_process_csv',
           'rule_group_provision_external_user',
           'rule_group_remove_external_user',
           'rule_group_check_external_user',
           'rule_group_user_exists',
           'api_group_search_users',
           'api_group_exists',
           'api_group_create',
           'api_group_update',
           'api_group_delete',
           'api_group_get_description',
           'api_group_user_is_member',
           'api_group_user_add',
           'api_group_user_update_role',
           'api_group_get_user_role',
           'api_group_remove_user_from_group']


def user_is_a_datamanager(ctx):
    """Return groups whether current user is datamanager of a group, not specifically of a specific group.

    :param ctx: Combined type of a ctx and rei struct

    :returns: Boolean indicating if user is a datamanager.
    """

    is_a_datamanager = False

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if group.is_member(ctx, row[0]):
            is_a_datamanager = True
            # no need to check for more - this user is a datamanager
            break

    return is_a_datamanager


def getGroupData(ctx):
    """Return groups and related data."""
    groups = {}

    # First query: obtain a list of groups with group attributes.
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        name = row[0]
        attr = row[1]
        value = row[2]

        # Create/update group with this information.
        try:
            group = groups[name]
        except Exception:
            group = {
                "name": name,
                "managers": [],
                "members": [],
                "read": []
            }
            groups[name] = group

        if attr in ["data_classification", "category", "subcategory"]:
            group[attr] = value
        elif attr == "description":
            # Deal with legacy use of '.' for empty description metadata.
            # See uuGroupGetDescription() in uuGroup.r for correct behavior of the old query interface.
            group[attr] = '' if value == '.' else value
        elif attr == "manager":
            group["managers"].append(value)

    # Second query: obtain list of groups with memberships.
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, USER_NAME, USER_ZONE",
        "USER_TYPE != 'rodsgroup'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        name = row[0]
        user = row[1]
        zone = row[2]

        if name != user and name != "rodsadmin" and name != "public":
            user = user + "#" + zone
            if name.startswith("read-"):
                # Match read-* group with research-* or initial-* group.
                name = name[5:]
                try:
                    # Attempt to add to read list of research group.
                    group = groups["research-" + name]
                    group["read"].append(user)
                except Exception:
                    try:
                        # Attempt to add to read list of initial group.
                        group = groups["initial-" + name]
                        group["read"].append(user)
                    except Exception:
                        pass
            elif not name.startswith("vault-"):
                # Ardinary group.
                group = groups[name]
                group["members"].append(user)

    return groups.values()


def getCategories(ctx):
    """Get a list of all group categories."""
    categories = []

    iter = genquery.row_iterator(
        "ORDER_DESC(META_USER_ATTR_VALUE)",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        categories.append(row[0])

    return categories


def getDatamanagerCategories(ctx):
    """Get a list of all datamanager group categories."""
    categories = []

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        datamanager_group = row[0]

        if user.is_member_of(ctx, datamanager_group):
            # Example: 'datamanager-initial' is groupname of datamanager, second part is category
            category = '-'.join(datamanager_group.split('-')[1:])
            categories.append(category)

    return categories


def getSubcategories(ctx, category):
    """Get a list of all subcategories within a given group category.

    :param ctx:      Combined type of a ctx and rei struct
    :param category: Category to retrieve subcategories of

    :returns: List of all subcategories within a given group category
    """
    categories = set()    # Unique subcategories.
    groupCategories = {}  # Group name => { category => .., subcategory => .. }

    # Collect metadata of each group into `groupCategories` until both
    # the category and subcategory are available, then add the subcategory
    # to `categories` if the category name matches.
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME LIKE '%category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        group = row[0]
        key = row[1]
        value = row[2]

        if group not in groupCategories:
            groupCategories[group] = {}

        if key in ['category', 'subcategory']:
            groupCategories[group][key] = value

        if ('category' in groupCategories[group]
           and 'subcategory' in groupCategories[group]):
            # Metadata complete, now filter on category.
            if groupCategories[group]['category'] == category:
                # Bingo, add to the subcategory list.
                categories.add(groupCategories[group]['subcategory'])

            del groupCategories[group]

    return list(categories)


def user_role(ctx, group_name, user):
    """Return role of user in group.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Group name of user
    :param user:       User to return type of

    :returns: User role ('none' | 'reader' | 'normal' | 'manager')
    """
    groups = getGroupData(ctx)
    if '#' not in user:
        import session_vars
        user = user + "#" + session_vars.get_map(ctx.rei)["client_user"]["irods_zone"]

    groups = list(filter(lambda group: group_name == group["name"] and (user in group["read"] or user in group["members"]), groups))

    if groups:
        if user in groups[0]["managers"]:
            return "manager"
        elif user in groups[0]["members"]:
            return "normal"
        elif user in groups[0]["read"]:
            return "reader"
    else:
        return "none"


def user_is_datamanager(ctx, category, user):
    """Return if user is datamanager of category.

    :param ctx:      Combined type of a ctx and rei struct
    :param category: Category to check if user is datamanger of
    :param user:     User to check if user is datamanger

    :returns: Boolean indicating if user is datamanager
    """
    return user_role(ctx, 'datamanager-{}'.format(category), user) \
        in ('normal', 'manager')


def group_category(ctx, group):
    """Return category of group.

    :param ctx:   Combined type of a ctx and rei struct
    :param group: Group to return category of

    :returns: Category name of group
    """
    if group.startswith('vault-'):
        group = ctx.uuGetBaseGroup(group, '')['arguments'][1]
    return ctx.uuGroupGetCategory(group, '', '')['arguments'][1]


@api.make()
def api_group_data(ctx):
    """Retrieve group data as hierarchy for user.

    The structure of the group hierarchy parameter is as follows:
    {
      'CATEGORY_NAME': {
        'SUBCATEGORY_NAME': {
          'GROUP_NAME': {
            'description': 'GROUP_DESCRIPTION',
            'data-classification': 'GROUP_DATA_CLASSIFICATION',
            'members': {
              'USER_NAME': {
                'access': (reader | normal | manager)
              }, ...
            }
          }, ...
        }, ...
      }, ...
    }

    :param ctx: Combined type of a ctx and rei struct

    :returns: Group hierarchy, user type and user zone
    """
    if user.is_admin(ctx):
        groups = getGroupData(ctx)
    else:
        groups    = getGroupData(ctx)
        full_name = user.full_name(ctx)

        categories = getDatamanagerCategories(ctx)

        # Filter groups (only return groups user is part of), convert to json and write to stdout.
        groups = list(filter(lambda group: full_name in group['read'] + group['members'] or group['category'] in categories, groups))

    # Sort groups on name.
    groups = sorted(groups, key=lambda d: d['name'])

    group_hierarchy = OrderedDict()
    for group in groups:
        group['members'] = sorted(group['members'])
        members = OrderedDict()

        # Normal users
        for member in group['members']:
            members[member] = {'access': 'normal'}

        # Managers
        for member in group['managers']:
            members[member] = {'access': 'manager'}

        # Read users
        for member in group['read']:
            members[member] = {'access': 'reader'}

        if not group_hierarchy.get(group['category']):
            group_hierarchy[group['category']] = OrderedDict()

        if not group_hierarchy[group['category']].get(group['subcategory']):
            group_hierarchy[group['category']][group['subcategory']] = OrderedDict()

        group_hierarchy[group['category']][group['subcategory']][group['name']] = {
            'description': group['description'] if 'description' in group else '',
            'data_classification': group['data_classification'] if 'data_classification' in group else '',
            'members': members
        }

    # order the resulting group_hierarchy and put System in as first category
    cat_list = []
    system_present = False
    for cat in group_hierarchy:
        if cat != 'System':
            cat_list.append(cat)
        else:
            system_present = True
    cat_list.sort()
    if system_present:
        cat_list.insert(0, 'System')

    new_group_hierarchy = OrderedDict()
    for cat in cat_list:
        new_group_hierarchy[cat] = group_hierarchy[cat]

    # Python 3 solution:
    # Put System category as first category.
    # if "System" in group_hierarchy:
    #    group_hierarchy.move_to_end("System", last=False)

    return {'group_hierarchy': new_group_hierarchy, 'user_type': user.user_type(ctx), 'user_zone': user.zone(ctx)}


@api.make()
def api_group_process_csv(ctx, csv_header_and_data, allow_update, delete_users):
    """Process contents of CSV file containing group definitions.

    Parsing is stopped immediately when an error is found and the rownumber is returned to the user.

    :param ctx:                 Combined type of a ctx and rei struct
    :param csv_header_and_data: CSV data holding a head conform description and the actual row data
    :param allow_update:        Allow updates in groups
    :param delete_users:         Allow for deleting of users from groups

    :returns: Dict containing status, error(s) and the resulting group definitions so the frontend can present the results

    """
    # only datamanagers are allowed to use this functionality
    if not user_is_a_datamanager(ctx):
        return api.Error('errors', ['Insufficient rights to perform this operation'])

    # step 1. Parse the data in the uploaded file
    data, error = parse_data(ctx, csv_header_and_data)
    if len(error):
        return api.Error('errors', [error])

    # step 2. validate the data
    validation_errors = validate_data(ctx, data, allow_update)
    if len(validation_errors) > 0:
        return api.Error('errors', validation_errors)

    # step 3. create/update groups
    # if not args.online_check: ????
    error = apply_data(ctx, data, allow_update, delete_users)
    if len(error):
        return api.Error('errors', [error])

    # all went well
    return api.Result.ok()


def parse_data(ctx, csv_header_and_data):
    """Process contents of csv data consisting of header and 1 row of data.

    :param ctx:                 Combined type of a ctx and rei struct
    :param csv_header_and_data: CSV data holding a head conform description and the actual row data

    :returns: Dict containing error and the extracted data
    """
    extracted_data = []

    csv_lines = csv_header_and_data.splitlines()
    header = csv_lines[0]
    import_lines = csv_lines[1:]

    # list of dicts each containg label / value pairs
    lines = []
    header_cols = header.split(',')
    for import_line in import_lines:
        data = import_line.split(',')
        if len(data) != len(header_cols):
            return [], 'Amount of header columns differs from data columns.'
        line_dict = {}
        for x in range(0, len(header_cols)):
            if header_cols[x] == '':
                if x == len(header_cols) - 1:
                    return [], "Header row ends with ','"
                else:
                    return [], 'Empty column description found in header row.'
            try:
                line_dict[header_cols[x]] = data[x]
            except (KeyError, IndexError):
                line_dict[header_cols[x]] = ''

        lines.append(line_dict)

    for line in lines:
        rowdata, error = _process_csv_line(ctx, line)

        if error is None:
            extracted_data.append(rowdata)
        else:
            # End processing of csv data due to erroneous input
            return extracted_data, "Data error: {}".format(error)

    return extracted_data, ''


def validate_data(ctx, data, allow_update):
    """Validation of extracted data.

    :param ctx:          Combined type of a ctx and rei struct
    :param data:         Data to be processed
    :param allow_update: Allow for updating of groups

    :returns: Errors if found any
    """
    def is_internal_user(username):
        for domain in config.external_users_domain_filter:
            domain_pattern = '@{}$'.format(domain)
            if re.search(domain_pattern, username) is not None:
                return True
        return False

    errors = []
    for (category, subcategory, groupname, managers, members, viewers) in data:

        if group.exists(ctx, groupname) and not allow_update:
            errors.append('Group "{}" already exists'.format(groupname))

        for the_user in managers + members + viewers:
            if not is_internal_user(the_user):
                # ensure that external users already have an iRODS account
                # we do not want to be the actor that creates them
                if not user.exists(ctx, the_user):
                    errors.append('Group {} has nonexisting external user {}'.format(groupname, the_user))
    return errors


def apply_data(ctx, data, allow_update, delete_users):
    """ Update groups with the validated data

    :param ctx:          Combined type of a ctx and rei struct
    :param data:         Data to be processed
    :param allow_update: Allow updates in groups
    :param delete_users:  Allow for deleting of users from groups

    :returns: Errors if found any
    """

    for (category, subcategory, groupname, managers, members, viewers) in data:
        new_group = False

        log.write(ctx, 'Adding and updating group: {}'.format(groupname))

        # First create the group. Note that the rodsadmin actor will become a groupmanager
        response = ctx.uuGroupAdd(groupname, category, subcategory, '', 'unspecified', '', '')['arguments']
        status = response[5]
        message = response[6]

        if ((status == '-1089000') | (status == '-809000')) and allow_update:
            log.write(ctx, 'WARNING: group "{}" not created, it already exists'.format(groupname))
        elif status != '0':
            return "Error while attempting to create group {}. Status/message: {} / {}".format(groupname, status, message)
        else:
            new_group = True

        # Now add the users and set their role if other than member
        allusers = managers + members + viewers
        log.write(ctx, 'allusers')
        log.write(ctx, allusers)
        for username in list(set(allusers)):   # duplicates removed
            currentrole = user_role(ctx, groupname, username)
            if currentrole == "none":
                response = ctx.uuGroupUserAdd(groupname, username, '', '')['arguments']
                status = response[2]
                message = response[3]
                if status == '0':
                    currentrole = "member"
                    log.write(ctx, "Notice: added user {} to group {}".format(username, groupname))
                else:
                    log.write(ctx, "Warning: error occurred while attempting to add user {} to group {}".format(username, groupname))
                    log.write(ctx, "Status: {} , Message: {}".format(status, message))
            else:
                log.write(ctx, "Notice: user {} is already present in group {}.".format(username, groupname))

            # Set requested role. Note that user could be listed in multiple roles.
            # In case of multiple roles, manager takes precedence over normal,
            # and normal over reader
            role = 'reader'
            if username in members:
                role = 'normal'
            if username in managers:
                role = 'manager'

            if _are_roles_equivalent(role, currentrole):
                log.write(ctx, "Notice: user {} already has role {} in group {}.".format(username, role, groupname))
            else:
                response = ctx.uuGroupUserChangeRole(groupname, username, role, '', '')['arguments']
                status = response[3]
                message = response[4]

                if status == '0':
                    log.write(ctx, "Notice: changed role of user {} in group {} to {}".format(username, groupname, role))
                else:
                    log.write(ctx, "Warning: error while attempting to change role of user {} in group {} to {}".format(username, groupname, role))
                    log.write(ctx, "Status: {} , Message: {}".format(status, message))

        # Always remove the rods user for new groups, unless it is in the
        # CSV file.
        if (new_group and "rods" not in allusers and user_role(ctx, groupname, "rods") != "none"):
            response = ctx.uuGroupUserRemove(groupname, "rods", '', '')['arguments']
            status = response[2]
            message = response[3]
            if status == "0":
                log.write(ctx, "Notice: removed rods user from group " + groupname)
            else:
                if status != 0:
                    log.write(ctx, "Warning: error while attempting to remove user rods from group {}".format(groupname))
                    log.write(ctx, "Status: {} , Message: {}".format(status, message))

        # Remove users not in sheet
        if delete_users:
            # build list of current users
            currentusers = []
            for prefix in ['read-', 'initial-', 'research-']:
                iter = genquery.row_iterator(
                    "USER_GROUP_NAME, USER_NAME, USER_ZONE",
                    "USER_TYPE != 'rodsgroup' AND USER_GROUP_NAME = '{}'".format(prefix + '-'.join(groupname.split('-')[1:])),
                    genquery.AS_LIST, ctx
                )

                for row in iter:
                    # append [user,groupname]
                    currentusers.append([row[1],row[0]])

            for userdata in currentusers:
                user = userdata[0]
                usergroupname= userdata[1]
                if user not in allusers:
                    if user in managers:
                        if len(managers) == 1:
                            log.write(ctx, "Error: cannot remove user {} from group {}, because he/she is the only group manager".format(user, usergroupname))
                            continue
                        else:
                            managers.remove(user)
                    log.write(ctx, "Removing user {} from group {}".format(user, usergroupname))

                    response = ctx.uuGroupUserRemove(usergroupname, user, '', '')['arguments']
                    status = response[2]
                    message = response[3]
                    if status != "0":
                        log.write(ctx, "Warning: error while attempting to remove user {} from group {}".format(user, usergroupname))
                        log.write(ctx, "Status: {} , Message: {}".format(status, message))

    return ''


def parse_csv_file(ctx):
    extracted_data = []
    row_number = 0

    # Validate header columns (should be first row in file)

    # are all all required fields present?
    for label in _get_csv_predefined_labels():
        if label not in reader.fieldnames:
            _exit_with_error(
                'CSV header is missing compulsory field "{}"'.format(label))

    # duplicate fieldnames present?
    duplicate_columns = _get_duplicate_columns(reader.fieldnames)
    if (len(duplicate_columns) > 0):
        _exit_with_error("File has duplicate column(s): " + str(duplicate_columns))

    # Start processing the actual group data rows
    for line in lines:
        row_number += 1
        rowdata, error = _process_csv_line(line)

        if error is None:
            extracted_data.append(rowdata)
        else:
            _exit_with_error("Data error in in row {}: {}".format(
                str(row_number), error))

    return extracted_data


def _get_csv_predefined_labels():
    return ['category', 'subcategory', 'groupname']


def _get_duplicate_columns(fields_list):
    fields_seen = set()
    duplicate_fields = set()

    for field in fields_list:
        if (field in _get_csv_predefined_labels() or field.startswith(("manager:", "viewer:", "member:"))):
            if field in fields_seen:
                duplicate_fields.add(field)
            else:
                fields_seen.add(field)

    return duplicate_fields


def _process_csv_line(ctx, line):
    """Process a line as found in the csv consisting of category, subcategory, groupname, managers, members and viewers."""
    def is_email(username):
        """Is this email a valid email?"""
        return re.search(r'@.*[^\.]+\.[^\.]+$', username) is not None

    def is_valid_category(name):
        """Is this name a valid (sub)category name?"""
        return re.search(r"^[a-zA-Z0-9\-_]+$", name) is not None

    def is_valid_groupname(name):
        """Is this name a valid group name (prefix such as "research-" can be omitted"""
        return re.search(r"^[a-zA-Z0-9\-]+$", name) is not None

    category = line['category'].strip().lower().replace('.', '')
    subcategory = line['subcategory'].strip()
    groupname = "research-" + line['groupname'].strip().lower()
    managers = []
    members = []
    viewers = []

    for column_name in line.keys():
        if column_name == '':
            return None, 'Column cannot have an empty label'
        elif column_name in _get_csv_predefined_labels():
            continue

        username = line.get(column_name)

        if isinstance(username, list):
            return None, "Data is present in an unlabelled column"

        username = username.strip().lower()

        if username == '':    # empty value
            continue
        elif not is_email(username):
            return None, 'Username "{}" is not a valid email address.'.format(
                username)
        # elif not is_valid_domain(username.split('@')[1]):
        #    return None, 'Username "{}" failed DNS domain validation - domain does not exist or has no MX records.'.format(username)

        if column_name.lower().startswith('manager:'):
            managers.append(username)
        elif column_name.lower().startswith('member:'):
            members.append(username)
        elif column_name.lower().startswith('viewer:'):
            viewers.append(username)
        else:
            return None, "Column label '{}' is neither predefined nor a valid role label.".format(column_name)

    if len(managers) == 0:
        return None, "Group must have a group manager"

    if not is_valid_category(category):
        return None, '"{}" is not a valid category name.'.format(category)

    if not is_valid_category(subcategory):
        return None, '"{}" is not a valid subcategory name.'.format(subcategory)

    if not is_valid_groupname(groupname):
        return None, '"{}" is not a valid group name.'.format(groupname)

    row_data = (category, subcategory, groupname, managers, members, viewers)
    return row_data, None


def _are_roles_equivalent(a, b):
    """Checks whether two roles are equivalent, Yoda and Yoda-clienttools use slightly different names."""
    r_role_names = ["viewer", "reader"]
    m_role_names = ["member", "normal"]

    if a == b:
        return True
    elif a in r_role_names and b in r_role_names:
        return True
    elif a in m_role_names and b in m_role_names:
        return True
    else:
        return False


def group_user_exists(ctx, group_name, username, include_readonly):
    groups = getGroupData(ctx)
    if '#' not in username:
        import session_vars
        username = username + "#" + session_vars.get_map(ctx.rei)["client_user"]["irods_zone"]

    if not include_readonly:
        groups = list(filter(lambda group: group_name == group["name"] and username in group["members"], groups))
    else:
        groups = list(filter(lambda group: group_name == group["name"] and (username in group["read"] or username in group["members"]), groups))

    return len(groups) == 1


def rule_group_user_exists(rule_args, callback, rei):
    """Check if a user is a member of the given group.

    rule_group_user_exists(group, user, includeRo, membership)
    If includeRo is true, membership of a group's read-only shadow group will be
    considered as well. Otherwise, the user must be a normal member or manager of
    the given group.

    :param rule_args: [0] Group to check for user membership
                      [1] User to check for membership
                      [2] Include read-only shadow group users
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
    """
    ctx = rule.Context(callback, rei)
    exists = group_user_exists(ctx, rule_args[0], rule_args[1], rule_args[2])
    rule_args[3] = "true" if exists else "false"


@api.make()
def api_group_categories(ctx):
    """Retrieve category list."""
    return getCategories(ctx)


@api.make()
def api_group_subcategories(ctx, category):
    """Retrieve subcategory list.

    :param ctx:      Combined type of a ctx and rei struct
    :param category: Category to retrieve subcategories of

    :returns: Subcategory list of specified category
    """
    return getSubcategories(ctx, category)


def provisionExternalUser(ctx, username, creatorUser, creatorZone):
    """Call External User Service API to add new user.

    :param ctx:         Combined type of a ctx and rei struct
    :param username:    Username of external user
    :param creatorUser: User creating the external user
    :param creatorZone: Zone of user creating the external user

    :returns: Response status code
    """
    eus_api_fqdn   = config.eus_api_fqdn
    eus_api_port   = config.eus_api_port
    eus_api_secret = config.eus_api_secret

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/add'

    data = {}
    data['username'] = username
    data['creator_user'] = creatorUser
    data['creator_zone'] = creatorZone

    try:
        response = requests.post(url, data=jsonutil.dump(data),
                                 headers={'X-Yoda-External-User-Secret':
                                          eus_api_secret},
                                 timeout=10,
                                 verify=False)
    except requests.ConnectionError or requests.ConnectTimeout:
        return -1

    return response.status_code


def rule_group_provision_external_user(rule_args, ctx, rei):
    """Provision external user."""
    status = 1
    message = "An internal error occurred."

    status = provisionExternalUser(ctx, rule_args[0], rule_args[1], rule_args[2])

    if status < 0:
        message = """Error: Could not connect to external user service.\n
                     Please contact a Yoda administrator"""
    elif status == 400:
        message = """Error: Invalid request to external user service.\n"
                     Please contact a Yoda administrator"""
    elif status == 401:
        message = """Error: Invalid user credentials for external user service.\n"
                     Please contact a Yoda administrator"""
    elif status == 403:
        message = """Error: Unauthorized request to external user service.\n"
                     Please contact a Yoda administrator"""
    elif status == 405:
        message = """Error: Invalid input for external user service.\n"
                     Please contact a Yoda administrator"""
    elif status == 415:
        message = """Error: Invalid input MIME type for external user service.\n"
                     Please contact a Yoda administrator"""
    elif status == 200 or status == 201 or status == 409:
        status = 0
        message = ""

    rule_args[3] = status
    rule_args[4] = message


def removeExternalUser(ctx, username, userzone):
    """Call External User Service API to remove user.

    :param ctx:      Combined type of a ctx and rei struct
    :param username: Username of user to remove
    :param userzone: Zone of user to remove

    :returns: Response status code
    """
    eus_api_fqdn   = config.eus_api_fqdn
    eus_api_port   = config.eus_api_port
    eus_api_secret = config.eus_api_secret

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/delete'

    data = {}
    data['username'] = username
    data['userzone'] = userzone

    response = requests.post(url, data=jsonutil.dump(data),
                             headers={'X-Yoda-External-User-Secret':
                                      eus_api_secret},
                             timeout=10,
                             verify=False)

    return str(response.status_code)


def rule_group_remove_external_user(rule_args, ctx, rei):
    """Remove external user."""
    log.write(ctx, removeExternalUser(ctx, rule_args[0], rule_args[1]))


@rule.make(inputs=[0], outputs=[1])
def rule_group_check_external_user(ctx, username):
    """Check that a user is external.

    :param ctx:      Combined type of a ctx and rei struct
    :param username: Name of the user (without zone) to check if external

    :returns: String indicating if user is external ('1': yes, '0': no)
    """
    user_and_domain = username.split("@")

    if len(user_and_domain) == 2:
        domain = user_and_domain[1]
        if domain not in config.external_users_domain_filter:
            return '1'

    return '0'


@api.make()
def api_group_search_users(ctx, pattern):
    (username, zone_name) = user.from_str(ctx, pattern)
    userList = list()

    userIter = genquery.row_iterator("USER_NAME, USER_ZONE",
                                     "USER_TYPE = 'rodsuser' AND USER_NAME LIKE '%{}%' AND USER_ZONE LIKE '%{}%'".format(username, zone_name),
                                     genquery.AS_LIST, ctx)

    adminIter = genquery.row_iterator("USER_NAME, USER_ZONE",
                                      "USER_TYPE = 'rodsadmin' AND USER_NAME LIKE '%{}%' AND USER_ZONE LIKE '%{}%'".format(username, zone_name),
                                      genquery.AS_LIST, ctx)

    for row in userIter:
        userList.append("{}#{}".format(row[0], row[1]))
    for row in adminIter:
        userList.append("{}#{}".format(row[0], row[1]))

    userList.sort()
    return userList


@api.make()
def api_group_exists(ctx, group_name):
    """Check if group exists.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group to check for existence

    :returns: Boolean indicating if group exists
    """
    return group.exists(ctx, group_name)


@api.make()
def api_group_create(ctx, group_name, category, subcategory, description, data_classification):
    """Create a new group.

    :param ctx:                 Combined type of a ctx and rei struct
    :param group_name:          Name of the group to create
    :param category:            Category of the group to create
    :param subcategory:         Subcategory of the group to create
    :param description:         Description of the group to create
    :param data_classification: Data classification of the group to create

    :returns: Dict with API status result
    """
    try:
        response = ctx.uuGroupAdd(group_name, category, subcategory, description, data_classification, '', '')['arguments']
        status = response[5]
        message = response[6]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong creating group "{}". Please contact a system administrator'.format(group_name))


@api.make()
def api_group_update(ctx, group_name, property_name, property_value):
    """Update group property.

    :param ctx:            Combined type of a ctx and rei struct
    :param group_name:     Name of the group to update property of
    :param property_name:  Name of the property to update
    :param property_value: Value of the property to update

    :returns: Dict with API status result
    """
    try:
        response = ctx.uuGroupModify(group_name, property_name, property_value, '', '')['arguments']
        status = response[3]
        message = response[4]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong updating group "{}". Please contact a system administrator'.format(group_name))


@api.make()
def api_group_delete(ctx, group_name):
    """Delete a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group to delete

    :returns: Dict with API status result
    """
    try:
        response = ctx.uuGroupRemove(group_name, '', '')['arguments']
        status = response[1]
        message = response[2]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong deleting group "{}". Please contact a system administrator'.format(group_name))


@api.make()
def api_group_get_description(ctx, group_name):
    """Retrieve description of a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group

    :returns: Description of the group
    """
    ruleResult = ctx.uuGroupGetDescription(group_name, '')

    description = ruleResult["arguments"][1]
    return description


@api.make()
def api_group_user_is_member(ctx, username, group_name):
    """Check if user is member of a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Boolean indicating if user is member of the group
    """
    return group_user_exists(ctx, group_name, username, True)


@api.make()
def api_group_user_add(ctx, username, group_name):
    """Add a user to a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Dict with API status result
    """
    try:
        response = ctx.uuGroupUserAdd(group_name, username, '', '')['arguments']
        status = response[2]
        message = response[3]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong adding {} to group "{}". Please contact a system administrator'.format(username, group_name))


@api.make()
def api_group_user_update_role(ctx, username, group_name, new_role):
    """Update role of a user in a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group
    :param new_role:   New role of the user

    :returns: Dict with API status result
    """
    try:
        response = ctx.uuGroupUserChangeRole(group_name, username, new_role, '', '')['arguments']
        status = response[3]
        message = response[4]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong updating role for {} in group "{}". Please contact a system administrator'.format(username, group_name))


@api.make()
def api_group_get_user_role(ctx, username, group_name):
    """Get role of a user in a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Role of the user
    """
    return user_role(ctx, group_name, username)


@api.make()
def api_group_remove_user_from_group(ctx, username, group_name):
    """Remove a user from a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Dict with API status result
    """
    # ctx.uuGroupUserRemove(group_name, username, '', '')
    try:
        response = ctx.uuGroupUserRemove(group_name, username, '', '')['arguments']
        status = response[2]
        message = response[3]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong removing {} from group "{}". Please contact a system administrator'.format(username, group_name))
