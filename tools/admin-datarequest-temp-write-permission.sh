#!/bin/sh
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/process-datarequest-temp-write-permission.r "'$1'" "'$2'" "'$3'"
