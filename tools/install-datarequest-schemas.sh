#!/bin/bash

# Set some parameters
zone=$1

# Insert datarequest schemas (overwrite if already present)
iput -f -r /etc/irods/irods-ruleset-uu/datarequest/schemas /$zone/yoda/datarequest
ichmod -rM inherit /$zone/yoda/datarequest/schemas
ichmod -rM read public /$zone/yoda/datarequest/schemas
