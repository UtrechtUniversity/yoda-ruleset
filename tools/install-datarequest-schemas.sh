#!/bin/bash

# Set some parameters
zone=$1

# Check if datarequest schemas collection exists
ils /$zone/yoda/datarequest/schemas > /dev/null 2>&1

# If not, copy whole directory
if [ $? -ne 0 ]; then
        iput -r /etc/irods/irods-ruleset-uu/datarequest/schemas /$zone/yoda/datarequest
        ichmod -rM inherit /$zone/yoda/datarequest/schemas
        ichmod -rM read public /$zone/yoda/datarequest/schemas

# If it does, check the presence of the individual schemas and copy those that are not present
else
        cd /etc/irods/irods-ruleset-uu/datarequest/
        find schemas -type f -name '*.json' -print0 | while read -d $'\0' schemapath; do
                ils /$zone/yoda/datarequest/$schemapath > /dev/null 2>&1
                if [ $? -ne 0 ]; then
                        coll=`echo $schemapath | sed 's/\(.*\)\/.*/\1/'`
                        file=`echo $schemapath | sed 's/.*\/\(.*\)/\1/'`
                        imkdir -p /$zone/yoda/datarequest/$coll
                        iput $schemapath /$zone/yoda/datarequest/$coll
                fi
        done
        cd - > /dev/null
fi
