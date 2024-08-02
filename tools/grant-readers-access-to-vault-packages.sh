#!/bin/bash
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/grant-readers-access-to-vault-packages.r '*dryRun="'$1'"' '*verbose="'$2'"'
