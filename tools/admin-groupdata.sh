#!/bin/sh
user=$1
irule -r irods_rule_engine_plugin-python-instance uuGetUserGroupData '*user="'$user'"' ruleExecOut
