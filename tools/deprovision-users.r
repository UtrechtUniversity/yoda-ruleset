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
        "GROUP(USER_NAME), COUNT(USER_GROUP_NAME)",
        "USER_TYPE = 'rodsuser' AND USER_ZONE = '{}'".format(zone),
        genquery.AS_TUPLE,
        callback) 

    # Include the users with two or less than two groups: one public and one personal group
    for row in userIter:
        if (int(row[1]) <= 2):
            userList.append("{}".format(row[0]))

    for user in userList:
        callback.writeLine("stdout", user)

INPUT null
OUTPUT ruleExecOut