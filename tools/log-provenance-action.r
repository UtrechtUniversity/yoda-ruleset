#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Logs an action in the provenance log
#
import genquery

def main(rule_args, callback, rei):
    collection = global_vars["*collection"].strip('"')
    actor = global_vars["*actor"].strip('"')
    action = global_vars["*action"].strip('"')
    callback.rule_provenance_log_action(actor, collection, action)

INPUT *collection="", *actor="rods", *action=""
OUTPUT ruleExecOut
