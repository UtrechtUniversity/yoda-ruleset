# usage: peps-to-csv.sh dynamic_peps.json
#
# dynamic_peps.json is the file in the irods_docs repo:
# https://github.com/irods/irods_docs/blob/4-2-stable/dynamic_peps.json
#
# Turns peps JSON into TAB-separated csv data.
# Depends on jq.

jq '.sigGroupList[] | .sigList[] | @text "\(.funcName) \t\([.paramList[] | @text "\(.paramName):\(.paramType)"] | join("\t"))"' -r "$@"
