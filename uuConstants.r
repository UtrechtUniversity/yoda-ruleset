# \file        uuConstants.r
# \brief       Constants that apply to all Yoda implementations.
# \author      Paul Frederiks
# \author      Lazlo Westerhof
# \copyright   Copyright (c) 2016-2022 Utrecht University. All rights reserved.
# \license     GPLv3, see LICENSE.

# \constants uuORGMETADATAPREFIX Prefix for organisational metadata
UUORGMETADATAPREFIX = "org_"

# \constant UUSYSTEMCOLLECTION   irods path of a system collection to store system support files in
# Needs to be prepended with irods zone.
UUSYSTEMCOLLECTION = "/yoda"

# \constant  UUREVISIONCOLLECTION   irods path where all revisions will be stored
UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION ++ "/revisions"

# \constant UUMAXREVISIONSIZE
UUMAXREVISIONSIZE = double("2000000000"); # 2GB as in 2 * 1000 * 1000 * 1000

# \constant UUBLOCKLIST
UUBLOCKLIST = list("._*", ".DS_Store");
