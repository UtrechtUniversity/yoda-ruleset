# \file      uuGroup.py
# \brief     Functions for group management and group queries.
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json

# \brief Return groups and related data.
#
def getGroupData(callback):
    groups = {}

    # First query: obtain a list of groups with group attributes.
    ret_val = callback.msiMakeGenQuery(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            name = result.sqlResult[0].row(row)
            attr = result.sqlResult[1].row(row)
            value = result.sqlResult[2].row(row)

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

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    # Second query: obtain list of groups with memberships.
    ret_val = callback.msiMakeGenQuery(
        "USER_GROUP_NAME, USER_NAME, USER_ZONE",
        "USER_TYPE != 'rodsgroup'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            name = result.sqlResult[0].row(row)
            user = result.sqlResult[1].row(row)
            zone = result.sqlResult[2].row(row)

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

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    return groups.values()


# \brief Get a list of all group categories.
#
def getCategories(callback):
    categories = []

    ret_val = callback.msiMakeGenQuery(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            categories.append(result.sqlResult[0].row(row))

        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    return categories


# \brief Get a list of all subcategories within a given group category.
#
# \param[in] category
#
def getSubcategories(callback, category):
    categories = set()    # Unique subcategories.
    groupCategories = {}  # Group name => { category => .., subcategory => .. }

    # Collect metadata of each group into `groupCategories` until both
    # the category and subcategory are available, then add the subcategory
    # to `categories` if the category name matches.
    ret_val = callback.msiMakeGenQuery(
        "USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME LIKE '%category'",
        irods_types.GenQueryInp())
    query = ret_val['arguments'][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val['arguments'][1]
        for row in range(result.rowCnt):
            group = result.sqlResult[0].row(row)
            key = result.sqlResult[1].row(row)
            value = result.sqlResult[2].row(row)

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

        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    return list(categories)


# \brief Write group data for all users to stdout.
#
def uuGetGroupData(rule_args, callback, rei):
    groups = getGroupData(callback)

    # Convert to json string and write to stdout.
    callback.writeString("stdout", json.dumps(groups))


# \brief Write group data for a single user to stdout.
#
def uuGetUserGroupData(rule_args, callback, rei):
    groups = getGroupData(callback)
    user = rule_args[0] + '#' + rule_args[1]

    # Filter groups (only return groups user is part of), convert to json and write to stdout.
    groups = list(filter(lambda group: user in group["read"] or user in group["members"], groups))
    callback.writeString("stdout", json.dumps(groups))


# \brief Check if a user is a member of the given group.
#
# groupUserExists(group, user, includeRo, membership)
# If includeRo is true, membership of a group's read-only shadow group will be
# considered as well. Otherwise, the user must be a normal member or manager of
# the given group.
#
def groupUserExists(rule_args, callback, rei):
    groups = getGroupData(callback)
    user = rule_args[1]
    if not '#' in user:
        import session_vars
        user = user + "#" + session_vars.get_map(rei)["client_user"]["irods_zone"]

    if rule_args[2] == "false":
        groups = list(filter(lambda group: rule_args[0] == group["name"] and user in group["members"], groups))
    else:
        groups = list(filter(lambda group: rule_args[0] == group["name"] and (user in group["read"] or user in group["members"]), groups))

    rule_args[3] = "true" if len(groups) == 1 else "false"


# \brief Write category list to stdout.
#
def uuGroupGetCategoriesJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getCategories(callback)))


# \brief Write subcategory list to stdout.
#
def uuGroupGetSubcategoriesJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getSubcategories(callback, rule_args[0])))


# \brief Retrieve config value from credentials store.
#
def credentialsStoreGet(key):
    config = json.loads(open('/var/lib/irods/.credentials_store/store_config.json').read())
    return config[key]


import requests

# \brief Call External User Service API to add new user
#
# \param[in] username
# \param[in] creatorUser
# \param[in] creatorZone
#
def provisionExternalUser(callback, username, creatorUser, creatorZone):
    eus_api_fqdn = credentialsStoreGet("eus_api_fqdn")
    eus_api_port = credentialsStoreGet("eus_api_port")
    eus_api_secret = credentialsStoreGet("eus_api_secret")

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/add'

    data = {}
    data['username'] = username
    data['creator_user'] = creatorUser
    data['creator_zone'] = creatorZone

    try:
        response = requests.post(url, data=json.dumps(data),
                                 headers={'X-Yoda-External-User-Secret':
                                          eus_api_secret},
                                 timeout=5,
                                 verify=False)
    except requests.ConnectionError or requests.ConnectTimeout:
        return -1

    return response.status_code


# \brief Provision external user
#
def uuProvisionExternalUser(rule_args, callback, rei):
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


# \brief Call External User Service API to remove user
#
# \param[in] username
# \param[in] userzone
#
def removeExternalUser(callback, username, userzone):
    eus_api_fqdn = credentialsStoreGet("eus_api_fqdn")
    eus_api_port = credentialsStoreGet("eus_api_port")
    eus_api_secret = credentialsStoreGet("eus_api_secret")

    url = 'https://' + eus_api_fqdn + ':' + eus_api_port + '/api/user/delete'

    data = {}
    data['username'] = username
    data['userzone'] = userzone

    response = requests.post(url, data=json.dumps(data),
                             headers={'X-Yoda-External-User-Secret':
                                      eus_api_secret},
                             verify=False)

    return str(response.status_code)

# \brief Remove external user
#
def uuRemoveExternalUser(rule_args, callback, rei):
    callback.writeString("serverLog", removeExternalUser(callback, rule_args[0], rule_args[1]))
