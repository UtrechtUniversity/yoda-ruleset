#!/bin/bash

[[ $# -eq 5 ]] || { echo "Expected 5 arguments" >&2; exit 2; }

is_b64_token() {
    local token="$1"

    # Check if argument is provided.
    [[ -z "$token" ]] && return 1

    # Check format and length (must be multiple of 4).
    [[ $token =~ ^[A-Za-z0-9+/]+={0,2}$ ]] && (( ${#token} % 4 == 0 ))
}

actor="$1"
coll_origin_b64="$2"
coll_target_b64="$3"
receiver_b64="$4"
retry_str_b64="$5"

for value in "$coll_origin_b64" "$coll_target_b64" "$receiver_b64" "$retry_str_b64"; do
    is_b64_token "$value" || { echo "Invalid encoded argument" >&2; exit 2; }
done

irule -r irods_rule_engine_plugin-irods_rule_language-instance \
      -F /etc/irods/yoda-ruleset/tools/copy-to-research.r \
      "*actor=\"${actor}\"" \
      "*coll_origin_b64=\"${coll_origin_b64}\"" \
      "*coll_target_b64=\"${coll_target_b64}\"" \
      "*receiver_b64=\"${receiver_b64}\"" \
      "*retry_str_b64=\"${retry_str_b64}\""
