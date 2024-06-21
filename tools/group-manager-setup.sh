#!/bin/bash

# \file
# \brief     UU - Group manager setup script.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, 2016, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

set -e

# Set error handling and enable tracing of steps
#set -uo pipefail
#set -x  # Trace steps

echo "Running command: iadmin lg | grep priv"
command_output=$(iadmin lg 2>&1 | grep priv) || echo "iadmin lg command failed with status $?"

priv_group_list=()
# Only read into the array if command_output is not empty
if [ -z "$command_output" ]; then
    echo "No groups containing 'priv' were found."
else
    echo "Groups found, proceeding to read into array."
    readarray -t priv_group_list <<< "$command_output"
fi

echo "List of groups containing 'priv':"
for group in "${priv_group_list[@]}"; do
    echo "$group"
done

RODS_ZONE=`iadmin lz`
RODS_USER=`iuserinfo | grep '^name:' | cut -d ' ' -f2`

: ${RODS_ZONE:?Could not get zone name from iadmin lz}
: ${RODS_USER:?Could not get user name from iuserinfo}

if ! [[ "$RODS_ZONE$RODS_USER" =~ ^[a-zA-Z0-9@._-]+$ ]]; then
	# If iadmin output contains whitespace or other strange characters,
	# do not run an 'irm -r' with the zone name in its path.
	echo "User or zone name contains invalid characters: '$RODS_USER', '$RODS_ZONE'"
	exit 1
fi

for GROUP_NAME in priv-group-add priv-category-add priv-admin; do
	# TODO: Replace this script with a rule file that calls the Sudo microservices.
    # Check if GROUP_NAME is already in priv_group_list
    if [[ " ${priv_group_list[*]} " =~ " $GROUP_NAME " ]]; then
        echo "Group $GROUP_NAME already exists. Skipping setup."
    else
        echo "Setting up group $GROUP_NAME"
        set -x
        iadmin mkgroup "$GROUP_NAME"
        iadmin atg "$GROUP_NAME" "$RODS_USER"
        ichmod -M own "$RODS_USER" "/$RODS_ZONE/home/$GROUP_NAME"
        irm -r "/$RODS_ZONE/home/$GROUP_NAME"
        imeta set -u "$GROUP_NAME" manager       "$RODS_USER#$RODS_ZONE"
        imeta set -u "$GROUP_NAME" category      "System"
        imeta set -u "$GROUP_NAME" subcategory   "Privileges"
        imeta set -u "$GROUP_NAME" description   "."
        set +x
    fi
	#iadmin rmgroup $GROUP_NAME
done
