#!/bin/sh
actor=$1
coll=$2
status=$3
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/process-deaccession-status-transitions.r '*actor="'"$actor"'"' '*coll="'"$coll"'"' '*status="'"$status"'"'