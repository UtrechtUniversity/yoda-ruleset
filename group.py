# -*- coding: utf-8 -*-
"""Functions for group management and group queries."""

__copyright__ = 'Copyright (c) 2018-2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import requests

import genquery

from util import *

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

       Arguments:
       category -- Category to retrieve subcategories of
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


def uuGetGroupData(rule_args, callback, rei):
    """Write group data for all users to stdout."""
    groups = getGroupData(callback)

    # Convert to json string and write to stdout.
    callback.writeString("stdout", jsonutil.dump(groups))


def uuGetUserGroupData(rule_args, callback, rei):
    """Write group data for a single user to stdout."""
    groups = getGroupData(callback)
    user = rule_args[0] + '#' + rule_args[1]

    # Filter groups (only return groups user is part of), convert to json and write to stdout.
    groups = list(filter(lambda group: user in group["read"] or user in group["members"], groups))
    callback.writeString("stdout", jsonutil.dump(groups))


def groupUserExists(rule_args, callback, rei):
    """Check if a user is a member of the given group.

       groupUserExists(group, user, includeRo, membership)
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


def uuGroupGetCategoriesJson(rule_args, callback, rei):
    """Write category list to stdout."""
    callback.writeString("stdout", jsonutil.dump(getCategories(callback)))


def uuGroupGetSubcategoriesJson(rule_args, callback, rei):
    """Write subcategory list to stdout."""
    callback.writeString("stdout", jsonutil.dump(getSubcategories(callback, rule_args[0])))


def credentialsStoreGet(key):
    """Retrieve config value from credentials store."""
    config = json.loads(open('/var/lib/irods/.credentials_store/store_config.json').read())
    return config[key]


def provisionExternalUser(callback, username, creatorUser, creatorZone):
    """Call External User Service API to add new user

    Arguments:
    username    --
    creatorUser --
    creatorZone --
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


def uuProvisionExternalUser(rule_args, callback, rei):
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

    Arguments:
    username --
    userzone --
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


def uuRemoveExternalUser(rule_args, callback, rei):
    """Remove external user."""
    callback.writeString("serverLog", removeExternalUser(callback, rule_args[0], rule_args[1]))
