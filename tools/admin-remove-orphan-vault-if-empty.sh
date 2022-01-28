#!/bin/sh
group="$2"
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/remove-orphan-vault-if-empty.r '*vaultName="'"$group"'"'
