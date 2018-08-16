#!/bin/bash

# \file
# \brief     UU - Group manager setup script.
# \author    Chris Smeele
# \copyright Copyright (c) 2015, 2016, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE

set -e

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

for GROUP_NAME in priv-group-add priv-category-add ; do
	# TODO: Replace this script with a rule file that calls the Sudo microservices.
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
done
