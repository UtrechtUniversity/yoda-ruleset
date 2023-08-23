#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Transform existing publications according to the new changes in the publication process.
# This script handles converting all the prefixes from yoda to version. 
# Additionally, this script will add prefix version to DOIAvailable and DOI Minted variables.
#
# 
import subprocess
import genquery
import session_vars

def main(rule_args, callback, rei):
    zone = session_vars.get_map(rei)['client_user']['irods_zone']

    # Changing yoda prefix -> version
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "USER_ZONE = '{}' AND META_COLL_ATTR_NAME LIKE 'org_publication_yoda%'".format(zone),
        genquery.AS_TUPLE,
        callback) 

    iter2 = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "USER_ZONE = '{}' AND META_COLL_ATTR_NAME in ('org_publication_DOIAvailable', 'org_publication_DOIMinted')".format(zone),
        genquery.AS_TUPLE,
        callback) 

    for row in iter:
        subprocess.call(["imeta", "mod", "-C", row[0], row[1], row[2], "n:{}".format(row[1].replace("yoda", "version")), "v:{}".format(row[2])])

    for row in iter2:
        attr_name = row[1].rsplit('_', 1)[0] + "_version" + row[1].split('_')[-1]
        subprocess.call(["imeta", "mod", "-C", row[0], row[1], row[2], "n:{}".format(attr_name), "v:{}".format(row[2])])

INPUT null
OUTPUT ruleExecOut