#!/bin/bash

COLLECTION="$1"
ACTOR="$2"
ACTION="$3"

if [ -z "$COLLECTION" ]
then echo "Error: missing collection parameter value."
     exit 1
fi

if [ -z "$ACTOR" ]
then echo "Error: missing actor parameter value."
     exit 1
fi

if [ -z "$ACTION" ]
then echo "Error: missing action parameter value."
     exit 1
fi

/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/log-provenance-action.r "*collection=$COLLECTION" "*actor=$ACTOR" "*action=$ACTION"
