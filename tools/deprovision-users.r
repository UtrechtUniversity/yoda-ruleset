#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Generate a list of users that are not part of any group
# 
import genquery
import session_vars

def main(rule_args, callback, rei):
    zone = session_vars.get_map(rei)['client_user']['irods_zone']
    userList = []

    # Get the user name and group count
    userIter = genquery.row_iterator(
        "USER_NAME, COUNT(USER_GROUP_NAME)",
        f"USER_TYPE = 'rodsuser' AND USER_ZONE = '{zone}'",
        genquery.AS_TUPLE,
        callback) 

    # Include the users with two or less than two groups: one public and one personal group
    for row in userIter:
        if (int(row[1]) <= 2):
            userList.append(f"{row[0]}")

    for user in userList:
        callback.writeLine("stdout", user)

INPUT null
OUTPUT ruleExecOut