# \file      uuConstants.py
# \brief     Constants that apply to all Yoda implementations.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Declaration of constants
UUORGMETADATAPREFIX = 'org_'
UUSYSTEMCOLLECTION = "/yoda"

# \constant UUREVISIONCOLLECTION iRODS path where all revisions will be stored
UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION + "/revisions"

# \constant UUDEFAULTRESOURCETIER Default name for a tier when none defined yet
UUDEFAULTRESOURCETIER = 'Standard'

# \constant UURESOURCETIERATTRNAME Metadata attribute for storage tier name
UURESOURCETIERATTRNAME = UUORGMETADATAPREFIX + 'storage_tier'

# \constant UUMETADATASTORAGEMONTH Metadata for calculated storage month
UUMETADATASTORAGEMONTH = UUORGMETADATAPREFIX + 'storage_data_month'
