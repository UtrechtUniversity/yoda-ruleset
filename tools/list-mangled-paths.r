#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# List which paths of collections in irods are inconsistent with its parent.
# Example: a slash may be missing or in the wrong place.
# This can happen due to a bug in irods, where the collection path is mangled
# after a collection with a multi-byte character is renamed.
# For more information: https://github.com/irods/irods/issues/6239
# 
# Example command to run:
# irule -r irods_rule_engine_plugin-python-instance -F tools/list-mangled-paths.r
import genquery
import session_vars


def main(rule_args, callback, rei):
    zone = session_vars.get_map(rei)['client_user']['irods_zone']
    
    callback.writeLine("stdout", "list-mangled-paths script started")

    # The easy condition to check is if the coll is missing a
    # slash at the position where parent coll and coll first diverge. Example:
    #  coll_good[len(parent_coll)]
    # '/'
    # coll_bad[len(parent_coll)]
    # 'g'
    userIter = genquery.Query(callback,
                            ['COLL_NAME', 'COLL_PARENT_NAME'],
                            "COLL_NAME like '/{}/%'".format(zone),
                            output=genquery.AS_LIST)

    for row in userIter:
        name = row[0]
        coll_parent = row[1]

        if name[len(coll_parent)] != '/':
            callback.writeLine("stdout", "coll parent: {}".format(coll_parent))
            callback.writeLine("stdout", "coll       : {}".format(name))

    callback.writeLine("stdout", "list-mangled-paths script finished")

INPUT null
OUTPUT ruleExecOut
