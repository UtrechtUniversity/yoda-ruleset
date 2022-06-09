#!/bin/sh
path="$1"
physical_path="$2"
timestamp="$3"

state=$(/var/lib/irods/msiExecCmd_bin/dmattr "$physical_path")
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/tape_archive/admin-tape-archive-set-state.r "'$path'" "'$timestamp'" "'$state'"
