#!/bin/bash

if [ -z "$1" ]
then
   echo "Error: this script needs a zone name argument."
   echo "For example: ./install-datarequest-schemas.sh testZone"
   exit 1
else
   zone="$1"
fi

# Upload datarequest schemas (overwrite if already present)
iput -f -r /etc/irods/yoda-ruleset/datarequest/schemas "/$zone/yoda/datarequest"
ichmod -rM inherit "/$zone/yoda/datarequest/schemas"
ichmod -rM read public "/$zone/yoda/datarequest/schemas"
