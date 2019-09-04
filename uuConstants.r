# \file        uuConstants.r
# \brief       Constants that apply to all Yoda implementations.
# \author      Paul Frederiks
# \author      Lazlo Westerhof
# \copyright   Copyright (c) 2016-2018 Utrecht University. All rights reserved.
# \license     GPLv3, see LICENSE.

# \constants uuORGMETADATAPREFIX Prefix for organisational metadata
UUORGMETADATAPREFIX = "org_"

# \constant uuUSERMETADATAPREFIX Prefix for user metadata
UUUSERMETADATAPREFIX = "usr_"

# \constant uuUSERMETADATAROOT JSONAVU namespace/json root for user metadata
UUUSERMETADATAROOT = "usr"

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

# \constant UUPRIMARYRESOURCES
UUPRIMARYRESOURCES = list("irodsResc");

# \constant UUREPLICATIONRESOURCE
UUREPLICATIONRESOURCE = "irodsRescRepl";

# \constant UUMAXREVISIONSIZE
UUMAXREVISIONSIZE = double("2000000000"); # 2GB as in 2 * 1000 * 1000 * 1000

# \constant UUBLACKLIST
UUBLACKLIST = list("._*", ".DS_Store");
