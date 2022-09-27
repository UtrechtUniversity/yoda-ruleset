#!/bin/sh
#
# mis-named POC script
#

user=$1
shift
property=$1
shift
value=`echo $* | base64 -di`

arg='uuUserModify("'$user'", "'$property'", '\'$value\'', *status, *message)'
/bin/irule -r irods_rule_engine_plugin-irods_rule_language-instance "$arg" null ruleExecOut
