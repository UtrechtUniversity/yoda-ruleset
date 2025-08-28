#!/bin/bash
actor="$1"
coll_origin="$2"
coll_target="$3"
retry_str="$4"
receiver="$actor"

irule -r irods_rule_engine_plugin-irods_rule_language-instance \
      -F /etc/irods/yoda-ruleset/tools/copy-to-research.r \
      "*actor=\"${actor}\"" \
      "*coll_origin=\"${coll_origin}\"" \
      "*coll_target=\"${coll_target}\"" \
      "*receiver=\"${receiver}\"" \
      "*retry_str=\"${retry_str}\""
