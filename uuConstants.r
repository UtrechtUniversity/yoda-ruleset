# \file
# \brief       Constants that apply to all yoda implementations
# \author      Paul Frederiks
# \copyright   Copyright (c) 2016-2017 Utrecht University. All rights reserved
# \license     GPLv3, see LICENSE

# \constants uuORGMETADATAPREFIX Prefix for organisational metadata
UUORGMETADATAPREFIX = "org_"

# \constant uuUSERMETADATAPREFIX Prefix for user metadata
UUUSERMETADATAPREFIX = "usr_"

# \constant UUSYSTEMCOLLECTION   irods path of a system collection to store system support files in
# Needs to be prepended with irods zone.
UUSYSTEMCOLLECTION = "/yoda"

# \constant  UUREVISIONCOLLECTION   irods path where all revisions will be stored
UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION ++ "/revisions"

# \RESOURCE AND TIER MANAGEMENT
# \Default name for a tier when none defined yet
UUDEFAULTRESOURCETIER = 'Standard';

# \Metadata attribute for storage tier name
UURESOURCETIERATTRNAME = UUORGMETADATAPREFIX ++ 'storage_tier';

# \Metadata for calculated storage month
UUMETADATASTORAGEMONTH =  UUORGMETADATAPREFIX ++ 'storage_data_month';

