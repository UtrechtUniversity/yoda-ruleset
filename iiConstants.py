# \file  iiConstants.py
# \brief Constants for the research rules. If architecture changes, only
# 	 this file needs be adapted.
#
# \author    Lazlo Westerhof
# \author    Chris Smeele
# \copyright Copyright (c) 2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \constant IIMETADATAJSONNAME Name of metadata JSON file
IIJSONMETADATA = "yoda-metadata.json"

# \constant IIMETADATAXMLNAME
IIMETADATAXMLNAME = "yoda-metadata.xml"

# \constant IIRESEARCHXSDNAME Name of the research XSD
IIRESEARCHXSDNAME = "research.xsd"

# \constant IIVAULTXSDNAME Name of the vault XSD
IIVAULTXSDNAME = "vault.xsd"

# The maximum file size that can be read into a string in memory,
# to prevent DOSing / out of control memory consumption.
IIDATA_MAX_SLURP_SIZE = 4*1024*1024 # 4 MiB

# Prefix of user metadata (applied via legacy XML metadata file changes).
UUUSERMETADATAPREFIX = "usr_"

# JSONAVU JSON root / namespace of user metadata (applied via JSON metadata file changes).
UUUSERMETADATAROOT = "usr"

# Prefix for organisational metadata.
UUORGMETADATAPREFIX = "org_"

# Cronjob states
CRONJOB_STATE = {
    'PENDING':       'CRONJOB_PENDING',
    'PROCESSING':    'CRONJOB_PROCESSING',
    'RETRY':         'CRONJOB_RETRY',
    'UNRECOVERABLE': 'CRONJOB_UNRECOVERABLE',
    'OK':            'CRONJOB_OK',
}
