#!/bin/sh
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/irods-ruleset-uu/tools/process-datarequest-temp-write-permission.r "'$1'" "'$2'" "'$3'"
