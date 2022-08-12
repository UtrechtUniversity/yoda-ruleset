#!/bin/sh
actor="$1"
path="$2"
physical_path="$3"
timestamp="$4"

state=$(/var/lib/irods/msiExecCmd_bin/dmattr "$physical_path")
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/tape_archive/admin-tape-archive-set-state.r "'$path'" "'$timestamp'" "'$state'"
