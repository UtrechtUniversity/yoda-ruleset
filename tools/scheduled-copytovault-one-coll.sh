#!/bin/sh
echo "$1"
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/copy-one-coll-to-vault.r '*coll="'$1'"'
