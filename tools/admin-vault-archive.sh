#!/bin/sh
actor=$1
coll=$2
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/prepare-vault-archive.r '*actor="'"$actor"'"' '*coll="'"$coll"'"'
