RODS_ZONE=`iadmin lz`

: ${RODS_ZONE:?Could not get zone name from iadmin lz}

imkdir /$RODS_ZONE/home/datarequests-research
ichmod write public /$RODS_ZONE/home/datarequests-research
