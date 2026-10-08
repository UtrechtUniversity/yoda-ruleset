#!/bin/sh

[ $# -eq 2 ] || [ $# -eq 3 ] || { echo "Expected 2 or 3 arguments" >&2; exit 2; }

is_b64_token() {
    token="$1"

    # Check if argument is provided.
    [ -z "$token" ] && return 1

    # Check format and length (must be multiple of 4).
    echo "$token" | grep -qE '^[A-Za-z0-9+/]+={0,2}$' && [ $((${#token} % 4)) -eq 0 ]
}

actor=$1
coll_b64=$2
status=$3

is_b64_token "$coll_b64" || { echo "Invalid encoded argument" >&2; exit 2; }
irule -r irods_rule_engine_plugin-irods_rule_language-instance -F /etc/irods/yoda-ruleset/tools/process-deaccession-status-transitions.r '*actor="'"$actor"'"' '*coll_b64="'"$coll_b64"'"' '*status="'"$status"'"'
