# -*- coding: utf-8 -*-
"""Functions for group management and group queries."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time
from collections import OrderedDict
from datetime import datetime

import genquery
import requests
import session_vars

import schema
import sram
from groups_import import parse_data
from util import *

__all__ = ['api_group_data',
           'api_group_categories',
           'api_group_subcategories',
           'api_group_process_csv',
           'rule_group_provision_external_user',
           'rule_group_remove_external_user',
           'rule_group_check_external_user',
           'rule_group_expiration_date_validate',
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
           'api_group_remove_user_from_group',
           'rule_group_sram_sync']


def getGroupsData(ctx):
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

        if attr in ["schema_id", "data_classification", "category", "subcategory"]:
            group[attr] = value
        elif attr in ('description', 'expiration_date'):
            # Deal with legacy use of '.' for empty description metadata and expiration date.
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

        if name not in (user, 'rodsadmin', 'public'):
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
                try:
                    # Ordinary group.
                    group = groups[name]
                    group["members"].append(user)
                except KeyError:
                    pass

    return groups.values()


def getGroupData(ctx, name):
    """Get data for one group."""
    group = None

    # First query: obtain a list of group attributes.
    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '{}' AND USER_TYPE = 'rodsgroup'".format(name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        attr = row[0]
        value = row[1]

        if group is None:
            group = {
                "name": name,
                "managers": [],
                "members": [],
                "read": []
            }

        # Update group with this information.
        if attr in ["schema_id", "data_classification", "category", "subcategory"]:
            group[attr] = value
        elif attr == "description" or attr == "expiration_date":
            # Deal with legacy use of '.' for empty description metadata and expiration date.
            # See uuGroupGetDescription() in uuGroup.r for correct behavior of the old query interface.
            group[attr] = '' if value == '.' else value
        elif attr == "manager":
            group["managers"].append(value)

    if group is None or name.startswith("vault-"):
        return group

    # Second query: obtain group memberships.
    iter = genquery.row_iterator(
        "USER_NAME, USER_ZONE",
        "USER_GROUP_NAME = '{}' AND USER_TYPE != 'rodsgroup'".format(name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        user = row[0]
        zone = row[1]

        if name not in (user, 'rodsadmin', 'public'):
            group["members"].append(user + "#" + zone)

    if name.startswith("research-"):
        name = name[9:]
    elif name.startswith("initial-"):
        name = name[8:]
    else:
        return group

    # Third query: obtain group read memberships.
    name = "read-" + name
    iter = genquery.row_iterator(
        "USER_NAME, USER_ZONE",
        "USER_GROUP_NAME = '{}' AND USER_TYPE != 'rodsgroup'".format(name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        user = row[0]
        zone = row[1]

        if user != name:
            group["read"].append(user + "#" + zone)

    return group


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
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME IN('category','subcategory')",
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


def user_role(ctx, username, group_name):
    """Get role of user in group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   User to return type of
    :param group_name: Group name of user

    :returns: User role ('none' | 'reader' | 'normal' | 'manager')
    """
    group = getGroupData(ctx, group_name)
    if '#' not in username:
        username = username + "#" + session_vars.get_map(ctx.rei)["client_user"]["irods_zone"]

    if group:
        if username in group["managers"]:
            return "manager"
        elif username in group["members"]:
            return "normal"
        elif username in group["read"]:
            return "reader"

    return "none"


"""API to get role of user in group."""
api_group_get_user_role = api.make()(user_role)


def user_is_datamanager(ctx, category, user):
    """Return if user is datamanager of category.

    :param ctx:      Combined type of a ctx and rei struct
    :param category: Category to check if user is datamanger of
    :param user:     User to check if user is datamanger

    :returns: Boolean indicating if user is datamanager
    """
    return user_role(ctx, user, 'datamanager-{}'.format(category)) \
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
        groups = getGroupsData(ctx)
    else:
        groups    = getGroupsData(ctx)
        full_name = user.full_name(ctx)

        categories = getDatamanagerCategories(ctx)

        # Filter groups (only return groups user is part of), convert to json and write to stdout.
        groups = list(filter(lambda group: full_name in group['read'] + group['members'] or group['category'] in categories, groups))

    # Sort groups on name.
    groups = sorted(groups, key=lambda d: d['name'])

    # Gather group creation dates.
    creation_dates = {}
    zone = user.zone(ctx)
    iter = genquery.row_iterator(
        "COLL_NAME, COLL_CREATE_TIME",
        "COLL_PARENT_NAME = '/{}/home' and COLL_NAME not like '/{}/home/vault-%' and COLL_NAME not like '/{}/home/grp-%'".format(zone, zone, zone),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        creation_dates[row[0]] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(row[1])))

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

        # Check whether schema_id is present on group level.
        # If not, collect it from the corresponding category
        if "schema_id" not in group:
            group["schema_id"] = schema.get_schema_collection(ctx, user.zone(ctx), group['name'])

        coll_name = "/{}/home/{}".format(user.zone(ctx), group['name'])

        group_hierarchy[group['category']][group['subcategory']][group['name']] = {
            'description': group['description'] if 'description' in group else '',
            'schema_id': group['schema_id'],
            'expiration_date': group['expiration_date'] if 'expiration_date' in group else '',
            'data_classification': group['data_classification'] if 'data_classification' in group else '',
            'creation_date': creation_dates[coll_name] if coll_name in creation_dates else '',
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

    # Per category the group data has to be ordered by subcat asc as well
    subcat_ordered_group_hierarchy = OrderedDict()
    for cat in new_group_hierarchy:
        subcats_data = new_group_hierarchy[cat]
        # order on subcat level per category
        subcat_ordered_group_hierarchy[cat] = OrderedDict(sorted(subcats_data.items(), key=lambda x: x[0]))

    return {'group_hierarchy': subcat_ordered_group_hierarchy, 'user_type': user.user_type(ctx), 'user_zone': user.zone(ctx)}


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


@api.make()
def api_group_process_csv(ctx, csv_header_and_data, allow_update, delete_users):
    """Process contents of CSV file containing group definitions.

    Parsing is stopped immediately when an error is found and the rownumber is returned to the user.

    :param ctx:                 Combined type of a ctx and rei struct
    :param csv_header_and_data: CSV data holding a head conform description and the actual row data
    :param allow_update:        Allow updates in groups
    :param delete_users:        Allow for deleting of users from groups

    :returns: Dict containing status, error(s) and the resulting group definitions so the frontend can present the results

    """
    # Only admins and datamanagers are allowed to use this functionality.
    if not user.is_admin(ctx) and not user_is_a_datamanager(ctx):
        return api.Error('errors', ['Insufficient rights to perform this operation'])

    # Step 1: Parse the data in the uploaded file.
    data, error = parse_data(ctx, csv_header_and_data)
    if len(error):
        return api.Error('errors', [error])

    # Step 2: Validate the data.
    validation_errors = validate_data(ctx, data, allow_update)
    if len(validation_errors) > 0:
        return api.Error('errors', validation_errors)

    # Step 3: Create / update groups.
    error = apply_data(ctx, data, allow_update, delete_users)
    if len(error):
        return api.Error('errors', [error])

    return api.Result.ok()


def validate_data(ctx, data, allow_update):
    """Validation of extracted data.

    :param ctx:          Combined type of a ctx and rei struct
    :param data:         Data to be processed
    :param allow_update: Allow for updating of groups

    :returns: Errors if found any
    """
    errors = []

    can_add_category = user.is_member_of(ctx, 'priv-category-add')
    is_admin = user.is_admin(ctx)

    for (category, subcategory, groupname, _managers, _members, _viewers, _schema_id, _expiration_date) in data:

        if group.exists(ctx, groupname) and not allow_update:
            errors.append('Group "{}" already exists'.format(groupname))

        # Is user admin or has category add privileges?
        if not (is_admin or can_add_category):
            if category not in getCategories(ctx):
                # Insufficient permissions to add new category.
                errors.append('Category {} does not exist and cannot be created due to insufficient permissions.'.format(category))
            elif subcategory not in getSubcategories(ctx, category):
                # Insufficient permissions to add new subcategory.
                errors.append('Subcategory {} does not exist and cannot be created due to insufficient permissions.'.format(subcategory))

    return errors


def apply_data(ctx, data, allow_update, delete_users):
    """ Update groups with the validated data

    :param ctx:          Combined type of a ctx and rei struct
    :param data:         Data to be processed
    :param allow_update: Allow updates in groups
    :param delete_users:  Allow for deleting of users from groups

    :returns: Errors if found any
    """

    for (category, subcategory, group_name, managers, members, viewers, schema_id, expiration_date) in data:
        new_group = False

        log.write(ctx, 'CSV import - Adding and updating group: {}'.format(group_name))

        # First create the group. Note that the actor will become a groupmanager
        if not len(schema_id):
            schema_id = config.default_yoda_schema
        response = group_create(ctx, group_name, category, subcategory, schema_id, expiration_date, '', 'unspecified')

        if response:
            new_group = True
        elif response.status == "error_group_exists" and allow_update:
            log.write(ctx, 'CSV import - WARNING: group "{}" not created, it already exists'.format(group_name))
        else:
            return "Error while attempting to create group {}. Status/message: {} / {}".format(group_name, response.status, response.status_info)

        # Now add the users and set their role if other than member
        allusers = managers + members + viewers
        for username in list(set(allusers)):   # duplicates removed
            currentrole = user_role(ctx, username, group_name)
            if currentrole == "none":
                response = group_user_add(ctx, username, group_name)
                if response:
                    currentrole = "normal"
                    log.write(ctx, "CSV import - Notice: added user {} to group {}".format(username, group_name))
                else:
                    log.write(ctx, "CSV import - Warning: error occurred while attempting to add user {} to group {}".format(username, group_name))
                    log.write(ctx, "CSV import - Status: {} , Message: {}".format(response.status, response.status_info))
            else:
                log.write(ctx, "CSV import - Notice: user {} is already present in group {}.".format(username, group_name))

            # Set requested role. Note that user could be listed in multiple roles.
            # In case of multiple roles, manager takes precedence over normal,
            # and normal over reader
            role = 'reader'
            if username in members:
                role = 'normal'
            if username in managers:
                role = 'manager'

            if _are_roles_equivalent(role, currentrole):
                log.write(ctx, "CSV import - Notice: user {} already has role {} in group {}.".format(username, role, group_name))
            else:
                response = group_user_update_role(ctx, username, group_name, role)

                if response:
                    log.write(ctx, "CSV import - Notice: changed role of user {} in group {} to {}".format(username, group_name, role))
                else:
                    log.write(ctx, "CSV import - Warning: error while attempting to change role of user {} in group {} to {}".format(username, group_name, role))
                    log.write(ctx, "CSV import - Status: {} , Message: {}".format(response.status, response.status_info))

        # Always remove the rods user for new groups, unless it is in the
        # CSV file.
        if (new_group and "rods" not in allusers and user_role(ctx, "rods", group_name) != "none"):
            response = group_remove_user_from_group(ctx, "rods", group_name)
            if response:
                log.write(ctx, "CSV import - Notice: removed rods user from group " + group_name)
            else:
                log.write(ctx, "CSV import - Warning: error while attempting to remove user rods from group {}".format(group_name))
                log.write(ctx, "CSV import - Status: {} , Message: {}".format(response.status, response.status_info))

        # Remove users not in sheet
        if delete_users:
            # build list of current users
            currentusers = []
            for prefix in ['read-', 'initial-', 'research-']:
                iter = genquery.row_iterator(
                    "USER_GROUP_NAME, USER_NAME, USER_ZONE",
                    "USER_TYPE != 'rodsgroup' AND USER_GROUP_NAME = '{}'".format(prefix + '-'.join(group_name.split('-')[1:])),
                    genquery.AS_LIST, ctx
                )

                for row in iter:
                    # append [user,group_name]
                    currentusers.append([row[1], row[0]])

            for userdata in currentusers:
                username = userdata[0]
                usergroupname = userdata[1]
                if username not in allusers:
                    if username in managers:
                        if len(managers) == 1:
                            log.write(ctx, "CSV import - Error: cannot remove user {} from group {}, because he/she is the only group manager".format(username, usergroupname))
                            continue
                        else:
                            managers.remove(username)

                    response = group_remove_user_from_group(ctx, username, usergroupname)
                    if response:
                        log.write(ctx, "CSV import - Removing user {} from group {}".format(username, usergroupname))
                    else:
                        log.write(ctx, "CSV import - Warning: error while attempting to remove user {} from group {}".format(username, usergroupname))
                        log.write(ctx, "CSV import - Status: {} , Message: {}".format(response.status, response.status_info))

    return ''


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
    group = getGroupData(ctx, group_name)
    if '#' not in username:
        username = username + "#" + session_vars.get_map(ctx.rei)["client_user"]["irods_zone"]

    if group:
        if not include_readonly:
            return username in group["members"]
        else:
            return username in group["read"] or username in group["members"]
    else:
        return False


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
    eus_api_fqdn       = config.eus_api_fqdn
    eus_api_port       = config.eus_api_port
    eus_api_secret     = config.eus_api_secret
    eus_api_tls_verify = config.eus_api_tls_verify

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
                                 verify=eus_api_tls_verify)
    except (requests.ConnectionError, requests.ConnectTimeout):
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
    elif status == 500:
        status = 0
        message = """Error: could not provision external user service.\n"
                     Please contact a Yoda administrator"""

    rule_args[3] = status
    rule_args[4] = message


def removeExternalUser(ctx, username, userzone):
    """Call External User Service API to remove user.

    :param ctx:      Combined type of a ctx and rei struct
    :param username: Username of user to remove
    :param userzone: Zone of user to remove

    :returns: Response status code
    """
    eus_api_fqdn       = config.eus_api_fqdn
    eus_api_port       = config.eus_api_port
    eus_api_secret     = config.eus_api_secret
    eus_api_tls_verify = config.eus_api_tls_verify

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/delete'

    data = {}
    data['username'] = username
    data['userzone'] = userzone

    response = requests.post(url, data=jsonutil.dump(data),
                             headers={'X-Yoda-External-User-Secret':
                                      eus_api_secret},
                             timeout=10,
                             verify=eus_api_tls_verify)

    return str(response.status_code)


@rule.make(inputs=[0, 1], outputs=[])
def rule_group_remove_external_user(ctx, username, userzone):
    """Remove external user from EUS

      :param ctx:      Combined type of a ctx and rei struct
      :param username: Name of user to remove
      :param userzone: Zone of user to remove

      :returns:        HTTP status code of remove request, or "0"
                       if insufficient permissions.
   """
    if user.is_admin(ctx):
        ret = removeExternalUser(ctx, username, userzone)
        ctx.writeLine("serverLog", "Status code for removing external user "
                                   + username + "#" + userzone
                                   + " : " + ret)
        return ret
    else:
        ctx.writeLine("serverLog", "Cannot remove external user "
                                   + username + "#" + userzone
                                   + " : need admin permissions.")
        return '0'


@rule.make(inputs=[0], outputs=[1])
def rule_group_check_external_user(ctx, username):
    """Check that a user is external.

    :param ctx:      Combined type of a ctx and rei struct
    :param username: Name of the user (without zone) to check if external

    :returns: String indicating if user is external ('1': yes, '0': no)
    """
    if config.enable_sram:
        # All users are internal when SRAM is enabled.
        return '0'

    if yoda_names.is_internal_user(username):
        return '0'
    return '1'


@rule.make(inputs=[0], outputs=[1])
def rule_group_expiration_date_validate(ctx, expiration_date):
    """Validation of expiration date.

    :param ctx:             Combined type of a callback and rei struct
    :param expiration_date: String containing date that has to be validated

    :returns: Indication whether expiration date is an accepted value
    """
    if expiration_date in ["", "."]:
        return 'true'

    try:
        if expiration_date != datetime.strptime(expiration_date, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError

        # Expiration date should be in the future
        if expiration_date <= datetime.now().strftime('%Y-%m-%d'):
            raise ValueError
        return 'true'
    except ValueError:
        return 'false'


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


def group_create(ctx, group_name, category, subcategory, schema_id, expiration_date, description, data_classification):
    """Create a new group.

    :param ctx:                 Combined type of a ctx and rei struct
    :param group_name:          Name of the group to create
    :param category:            Category of the group to create
    :param subcategory:         Subcategory of the group to create
    :param schema_id:           Schema-id for the group to be created
    :param expiration_date:     Retention period for the group
    :param description:         Description of the group to create
    :param data_classification: Data classification of the group to create

    :returns: Dict with API status result
    """
    try:
        co_identifier = ''

        # Post SRAM collaboration and connect to service if SRAM is enabled.
        if config.enable_sram:
            response_sram = sram.sram_post_collaboration(ctx, group_name, description)

            if "error" in response_sram:
                message = response_sram['message']
                return api.Error('sram_error', message)
            else:
                co_identifier = response_sram['identifier']
                short_name = response_sram['short_name']

            if not sram.sram_connect_service_collaboration(ctx, short_name):
                return api.Error('sram_error', 'Something went wrong connecting service to group "{}" in SRAM'.format(group_name))

        response = ctx.uuGroupAdd(group_name, category, subcategory, schema_id, expiration_date, description, data_classification, co_identifier, '', '')['arguments']
        status = response[8]
        message = response[9]
        if status == '0':
            return api.Result.ok()
        elif status == '-1089000' or status == '-809000':
            return api.Error('group_exists', "Group {} not created, it already exists".format(group_name))
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong creating group "{}". Please contact a system administrator'.format(group_name))


"""API to create a new group."""
api_group_create = api.make()(group_create)


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
        # Delete SRAM collaboration if group is a SRAM group.
        if config.enable_sram:
            sram_group, co_identifier = sram_enabled(ctx, group_name)

        response = ctx.uuGroupRemove(group_name, '', '')['arguments']
        status = response[1]
        message = response[2]
        if status != '0':
            return api.Error('policy_error', message)

        if config.enable_sram and sram_group:
            if not sram.sram_delete_collaboration(ctx, co_identifier):
                return api.Error('sram_error', 'Something went wrong deleting group "{}" in SRAM'.format(group_name))

        return api.Result.ok()
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


def group_user_add(ctx, username, group_name):
    """Add a user to a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Dict with API status result
    """
    try:
        sram_group = False
        co_identifier = ''

        if config.enable_sram:
            sram_group, co_identifier = sram_enabled(ctx, group_name)
            if sram_group:
                # Validate email
                if not yoda_names.is_email_username(username):
                    return api.Error('invalid_email', 'User {} cannot be added to group {} because user email is invalid'.format(username, group_name))

        response = ctx.uuGroupUserAdd(group_name, username, '', '')['arguments']
        status = response[2]
        message = response[3]
        if status == '0':
            # Send invitation mail for SRAM CO.
            if config.enable_sram and sram_group:
                if config.sram_flow == 'join_request':
                    sram.invitation_mail_group_add_user(ctx, group_name, username.split('#')[0], co_identifier)
                elif config.sram_flow == 'invitation':
                    sram.sram_put_collaboration_invitation(ctx, group_name, username.split('#')[0], co_identifier)

            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong adding {} to group "{}". Please contact a system administrator'.format(username, group_name))


"""API to add a user to a group."""
api_group_user_add = api.make()(group_user_add)


def group_user_update_role(ctx, username, group_name, new_role):
    """Update role of a user in a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group
    :param new_role:   New role of the user

    :returns: Dict with API status result
    """
    try:
        if config.enable_sram:
            # Only call SRAM when changing between normal and manager roles.
            if new_role == "reader" and user_role(ctx, username, group_name) != "normal":
                sram_group, co_identifier = sram_enabled(ctx, group_name)
                if sram_group:
                    uid = sram.sram_get_uid(ctx, co_identifier, username)
                    if uid == '':
                        return api.Error('sram_error', 'Something went wrong getting the unique user id for user {} from SRAM. Please contact a system administrator.'.format(username))
                    elif not sram.sram_update_collaboration_membership(ctx, co_identifier, uid, new_role):
                        return api.Error('sram_error', 'Something went wrong updating role for {} user.'.format(username))

        response = ctx.uuGroupUserChangeRole(group_name, username, new_role, '', '')['arguments']
        status = response[3]
        message = response[4]
        if status == '0':
            return api.Result.ok()
        else:
            return api.Error('policy_error', message)
    except Exception:
        return api.Error('error_internal', 'Something went wrong updating role for {} in group "{}". Please contact a system administrator'.format(username, group_name))


"""API to update role of a user in a group."""
api_group_user_update_role = api.make()(group_user_update_role)


def group_remove_user_from_group(ctx, username, group_name):
    """Remove a user from a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Dict with API status result
    """
    try:
        if config.enable_sram:
            sram_group, co_identifier = sram_enabled(ctx, group_name)

        response = ctx.uuGroupUserRemove(group_name, username, '', '')['arguments']
        status = response[2]
        message = response[3]
        if status != '0':
            return api.Error('policy_error', message)

        if config.enable_sram and sram_group:
            uid = sram.sram_get_uid(ctx, co_identifier, username)
            if uid == '':
                return api.Error('sram_error', 'Something went wrong getting the unique user id for user {} from SRAM. Please contact a system administrator.'.format(username))
            else:
                if not sram.sram_delete_collaboration_membership(ctx, co_identifier, uid):
                    return api.Error('sram_error', 'Something went wrong removing {} from group "{}" in SRAM'.format(username, group_name))

        return api.Result.ok()
    except Exception:
        return api.Error('error_internal', 'Something went wrong removing {} from group "{}". Please contact a system administrator'.format(username, group_name))


"""API to remove a user from a group."""
api_group_remove_user_from_group = api.make()(group_remove_user_from_group)


def sram_enabled(ctx, group_name):
    """Checks if the group is SRAM enabled

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group

    :returns: enable_sram_flag as True and SRAM CO Identifier if the group is SRAM enabled else False and empty string
    """
    enable_sram_flag = False
    co_identifier = ''

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'co_identifier' AND USER_GROUP_NAME = '{}'".format(group_name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if row[0]:
            enable_sram_flag = True
            co_identifier = row[0]

    return enable_sram_flag, co_identifier


@rule.make()
def rule_group_sram_sync(ctx):
    """Synchronize groups with SRAM.

    :param ctx: Combined type of a ctx and rei struct
    """
    if not user.is_admin(ctx):
        return

    if not config.enable_sram:
        log.write(ctx, "SRAM needs to be enabled to sync groups")
        return

    log.write(ctx, "Start syncing groups with SRAM")
    groups = getGroupsData(ctx)

    for group in groups:
        group_name = group["name"]
        members = group['members'] + group['read']
        managers = group['managers']
        description = group['description'] if 'description' in group else ''

        log.write(ctx, "Sync group {} with SRAM".format(group_name))

        sram_group, co_identifier = sram_enabled(ctx, group_name)
        # Post collaboration group is not yet already SRAM enabled.
        if not sram_group:
            response_sram = sram.sram_post_collaboration(ctx, group_name, description)

            if "error" in response_sram:
                message = response_sram['message']
                log.write(ctx, "Something went wrong creating group {} in SRAM: {}".format(group_name, message))
                break
            else:
                co_identifier = response_sram['identifier']
                short_name = response_sram['short_name']
                avu.associate_to_group(ctx, group_name, "co_identifier", co_identifier)

            if not sram.sram_connect_service_collaboration(ctx, short_name):
                log.write(ctx, "Something went wrong connecting service to group {} in SRAM".format(group_name))
                break

        log.write(ctx, "Get members of group {} from SRAM".format(group_name))
        co_members = sram.sram_get_co_members(ctx, co_identifier)

        log.write(ctx, "Sync members of group {} with SRAM".format(group_name))
        for member in members:
            # Validate email
            if not yoda_names.is_email_username(member):
                log.write(ctx, "User {} cannot be added to group {} because user email is invalid".format(member, group_name))
                continue

            if member.split('#')[0] not in co_members:
                if config.sram_flow == 'join_request':
                    sram.invitation_mail_group_add_user(ctx, group_name, member.split('#')[0], co_identifier)
                    log.write(ctx, "User {} added to group {}".format(member, group_name))
                elif config.sram_flow == 'invitation':
                    sram.sram_put_collaboration_invitation(ctx, group_name, member.split('#')[0], co_identifier)
                    log.write(ctx, "User {} added to group {}".format(member, group_name))
            else:
                if member in managers:
                    uid = sram.sram_get_uid(ctx, co_identifier, member)
                    if uid == '':
                        log.write(ctx, "Something went wrong getting the SRAM user id for user {} of group {}".format(member, group_name))
                    else:
                        if sram.sram_update_collaboration_membership(ctx, co_identifier, uid, "manager"):
                            log.write(ctx, "Updated {} user to manager of group {}".format(member, group_name))
                        else:
                            log.write(ctx, "Something went wrong updating {} user to manager of group {} in SRAM".format(member, group_name))

    log.write(ctx, "Finished syncing groups with SRAM")
