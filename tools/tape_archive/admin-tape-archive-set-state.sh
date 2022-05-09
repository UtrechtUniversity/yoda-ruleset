#!/bin/sh
path="$1"
timestamp="$2"
state="$3"
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/tape_archive/admin-tape-archive-set-state.r "'$1'" "'$2'" "'$3'"
