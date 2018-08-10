# \file      uuGroup.py
# \brief     Functions for group management and group queries.
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2018 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Return groups and related data
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
            if attr == "description" or attr == "category" or attr == "subcategory":
                group[attr] = value
            if attr == "manager":
                group["managers"].append(value)

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)

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

    return groups.values()


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
