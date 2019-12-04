# -*- coding: utf-8 -*-
"""Functions for group management and group queries."""

__copyright__ = 'Copyright (c) 2018-2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import requests

import genquery

from util import *

__all__ = ['api_uu_group_data',
           'api_uu_group_data_filtered',
           'api_uu_group_categories',
           'api_uu_group_subcategories',
           'rule_uu_group_provision_external_user',
           'rule_uu_group_remove_external_user',
           'rule_uu_group_user_exists']


def getGroupData(callback):
    """Return groups and related data."""
    groups = {}

    # First query: obtain a list of groups with group attributes.
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup'",
        genquery.AS_LIST, callback
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
        genquery.AS_LIST, callback
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


def getCategories(callback):
    """Get a list of all group categories."""
    categories = []

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        categories.append(row[0])

    return categories


def getSubcategories(callback, category):
    """
       Get a list of all subcategories within a given group category.

       :param category: Category to retrieve subcategories of
    """
    categories = set()    # Unique subcategories.
    groupCategories = {}  # Group name => { category => .., subcategory => .. }

    # Collect metadata of each group into `groupCategories` until both
    # the category and subcategory are available, then add the subcategory
    # to `categories` if the category name matches.
    iter = genquery.row_iterator(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME LIKE '%category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        group = row[0]
        key = row[1]
        value = row[2]

        if group not in groupCategories:
            groupCategories[group] = {}

        if key in ['category', 'subcategory']:
            groupCategories[group][key] = value

        if ('category' in groupCategories[group] and
            'subcategory' in groupCategories[group]):
            # Metadata complete, now filter on category.
            if groupCategories[group]['category'] == category:
                # Bingo, add to the subcategory list.
                categories.add(groupCategories[group]['subcategory'])

            del groupCategories[group]

    return list(categories)


@api.make()
def api_uu_group_data(ctx):
    """Write group data for all users to stdout."""
    return getGroupData(ctx)


@api.make()
def api_uu_group_data_filtered(ctx, user_name, zone_name):
    """Write group data for a single user to stdout."""
    groups    = getGroupData(ctx)
    full_name = '{}#{}'.format(user_name, zone_name)

    # Filter groups (only return groups user is part of), convert to json and write to stdout.
    return list(filter(lambda group: full_name in group['read'] + group['members'], groups))


def rule_uu_group_user_exists(rule_args, callback, rei):
    """Check if a user is a member of the given group.

    rule_uu_group_user_exists(group, user, includeRo, membership)
    If includeRo is true, membership of a group's read-only shadow group will be
    considered as well. Otherwise, the user must be a normal member or manager of
    the given group.
    """
    groups = getGroupData(callback)
    user = rule_args[1]
    if '#' not in user:
        import session_vars
        user = user + "#" + session_vars.get_map(rei)["client_user"]["irods_zone"]

    if rule_args[2] == "false":
        groups = list(filter(lambda group: rule_args[0] == group["name"] and user in group["members"], groups))
    else:
        groups = list(filter(lambda group: rule_args[0] == group["name"] and (user in group["read"] or user in group["members"]), groups))

    rule_args[3] = "true" if len(groups) == 1 else "false"


@api.make()
def api_uu_group_categories(ctx):
    """Write category list to stdout."""
    return getCategories(ctx)


@api.make()
def api_uu_group_subcategories(ctx, category):
    """Write subcategory list to stdout."""
    return getSubcategories(ctx, category)


def credentialsStoreGet(key):
    """Retrieve config value from credentials store."""
    config = json.loads(open('/var/lib/irods/.credentials_store/store_config.json').read())
    return config[key]


def provisionExternalUser(callback, username, creatorUser, creatorZone):
    """Call External User Service API to add new user

    :param username: Username of external user
    :param creatorUser: User creating the external user
    :param creatorZone: Zone of user creating the external user
    """
    eus_api_fqdn = credentialsStoreGet("eus_api_fqdn")
    eus_api_port = credentialsStoreGet("eus_api_port")
    eus_api_secret = credentialsStoreGet("eus_api_secret")

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/add'

    data = {}
    data['username'] = username
    data['creator_user'] = creatorUser
    data['creator_zone'] = creatorZone

    try:
        response = requests.post(url, data=jsonutil.dump(data),
                                 headers={'X-Yoda-External-User-Secret':
                                          eus_api_secret},
                                 timeout=5,
                                 verify=False)
    except requests.ConnectionError or requests.ConnectTimeout:
        return -1

    return response.status_code


def rule_uu_group_provision_external_user(rule_args, callback, rei):
    """Provision external user."""
    status = 1
    message = "An internal error occured."

    status = provisionExternalUser(callback, rule_args[0], rule_args[1], rule_args[2])

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


def removeExternalUser(callback, username, userzone):
    """Call External User Service API to remove user.

    :param username: Username of user to remove
    :param userzone: Zone of user to remove
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
                             verify=False)

    return str(response.status_code)


def rule_uu_group_remove_external_user(rule_args, callback, rei):
    """Remove external user."""
    log.write(callback, removeExternalUser(callback, rule_args[0], rule_args[1]))
