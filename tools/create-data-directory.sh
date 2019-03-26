#!/bin/bash

# \file      create-data-directory.sh
# \brief     Initializes the data request data directory in which data requests (and related files) are stored.
#            Called by Ansible.
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Get iRODS zone
RODS_ZONE=`iadmin lz`
: ${RODS_ZONE:?Could not get zone name from iadmin lz}

# Create data directory
imkdir /$RODS_ZONE/home/datarequests-research

# Set permissions: all users must be able to write to the directory (you don't
# need permission to submit a data request)
ichmod write public /$RODS_ZONE/home/datarequests-research
