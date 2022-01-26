# -*- coding: utf-8 -*-
"""Functions for group management and group queries."""

__copyright__ = 'Copyright (c) 2018-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import requests

from util import *

__all__ = ['api_group_data',
           'api_group_categories',
           'api_group_subcategories',
           'rule_group_provision_external_user',
           'rule_group_remove_external_user',
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
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        categories.append(row[0])

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
        # Filter groups (only return groups user is part of), convert to json and write to stdout.
        groups = list(filter(lambda group: full_name in group['read'] + group['members'], groups))

    group_hierarchy = {}
    for group in groups:
        members = {}

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
            group_hierarchy[group['category']] = {}

        if not group_hierarchy[group['category']].get(group['subcategory']):
            group_hierarchy[group['category']][group['subcategory']] = {}

        group_hierarchy[group['category']][group['subcategory']][group['name']] = {
            'description': group['description'] if 'description' in group else '',
            'data_classification': group['data_classification'] if 'data_classification' in group else '',
            'members': members
        }

    return {'group_hierarchy': group_hierarchy, 'user_type': user.user_type(ctx), 'user_zone': user.zone(ctx)}


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
    eus_api_fqdn = credentialsStoreGet("eus_api_fqdn")
    eus_api_port = credentialsStoreGet("eus_api_port")
    eus_api_secret = credentialsStoreGet("eus_api_secret")

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

    :returns: Dict holding process status and process status info
    """
    try:
        response = ctx.uuGroupAdd(group_name, category, subcategory, description, data_classification, '', '')['arguments']
        status = response[5]
        message = response[6]
        return {'proc_status': status,
                'proc_status_info': message}
    except Exception:
        return {'proc_status': 'NOK',
                'proc_status_info': 'Something went wrong creating group "{}". Please contact a system administrator'.format(group_name)}


@api.make()
def api_group_update(ctx, group_name, property_name, property_value):
    """Update group property.

    :param ctx:            Combined type of a ctx and rei struct
    :param group_name:     Name of the group to update property of
    :param property_name:  Name of the property to update
    :param property_value: Value of the property to update

    :returns: Dict holding process status and process status info
    """
    try:
        response = ctx.uuGroupModify(group_name, property_name, property_value, '', '')['arguments']
        status = response[3]
        message = response[4]
        return {'proc_status': status,
                'proc_status_info': message}
    except Exception:
        return {'proc_status': 'NOK',
                'proc_status_info': 'Something went wrong updating group "{}". Please contact a system administrator'.format(group_name)}


@api.make()
def api_group_delete(ctx, group_name):
    """Delete a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param group_name: Name of the group to delete
    """
    ctx.uuGroupRemove(group_name, '', '')


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
    """
    ctx.uuGroupUserAdd(group_name, username, '', '')


@api.make()
def api_group_user_update_role(ctx, username, group_name, new_role):
    """Update role of a user in a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group
    :param new_role:   New role of the user
    """
    ctx.uuGroupUserChangeRole(group_name, username, new_role, '', '')


@api.make()
def api_group_get_user_role(ctx, username, group_name):
    """Get role of a user in a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group

    :returns: Role of the user
    """
    ruleResult = ctx.uuGroupGetMemberType(group_name, username, '')

    role = ruleResult["arguments"][2]
    return role


@api.make()
def api_group_remove_user_from_group(ctx, username, group_name):
    """Remove a user from a group.

    :param ctx:        Combined type of a ctx and rei struct
    :param username:   Name of the user
    :param group_name: Name of the group
    """
    ctx.uuGroupUserRemove(group_name, username, '', '')
