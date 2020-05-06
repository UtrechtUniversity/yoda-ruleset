# -*- coding: utf-8 -*-
"""Constants that apply to all Yoda environments."""

__copyright__ = 'Copyright (c) 2016-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from enum import Enum

# TODO: Naming convention (no capitals, no UU/II prefix)
# TODO: dicts => enum.Enum
# TODO: all attrnames => one enum.Enum

IIGROUPPREFIX = "research-"
IIGRPPREFIX = "grp-"

UUORGMETADATAPREFIX = 'org_'
UUSYSTEMCOLLECTION = '/yoda'

UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION + '/revisions'
"""iRODS path where all revisions will be stored."""

UUDEFAULTRESOURCETIER = 'Standard'
"""Default name for a tier when none defined yet."""

UURESOURCETIERATTRNAME = UUORGMETADATAPREFIX + 'storage_tier'
"""Metadata attribute for storage tier name."""

UUMETADATASTORAGEMONTH = UUORGMETADATAPREFIX + 'storage_data_month'
"""Metadata for calculated storage month."""

IILICENSECOLLECTION = UUSYSTEMCOLLECTION + '/licenses'
"""iRODS path where all licenses will be stored."""

IIJSONMETADATA = 'yoda-metadata.json'
"""Name of metadata JSON file."""

IIMETADATAXMLNAME = 'yoda-metadata.xml'
"""Name of metadata XML file."""

IIRESEARCHXSDNAME = 'research.xsd'
"""Name of the research XSD."""

IIVAULTXSDNAME = 'vault.xsd'
"""Name of the vault XSD."""

IIDATA_MAX_SLURP_SIZE = 4 * 1024 * 1024  # 4 MiB
"""The maximum file size that can be read into a string in memory, to prevent
   DOSing / out of control memory consumption."""

UUUSERMETADATAPREFIX = 'usr_'
"""Prefix of user metadata (applied via legacy XML metadata file changes)."""

UUUSERMETADATAROOT = 'usr'
"""JSONAVU JSON root / namespace of user metadata (applied via JSON metadata file changes)."""

UUORGMETADATAPREFIX = 'org_'
"""Prefix for organisational metadata."""

IILOCKATTRNAME        = UUORGMETADATAPREFIX + 'lock'
IISTATUSATTRNAME      = UUORGMETADATAPREFIX + 'status'
IIVAULTSTATUSATTRNAME = UUORGMETADATAPREFIX + 'vault_status'

CRONJOB_STATE = {
    'PENDING':       'CRONJOB_PENDING',
    'PROCESSING':    'CRONJOB_PROCESSING',
    'RETRY':         'CRONJOB_RETRY',
    'UNRECOVERABLE': 'CRONJOB_UNRECOVERABLE',
    'OK':            'CRONJOB_OK',
}
"""Cronjob states."""


class vault_package_state(Enum):
    """Vault package states."""

    # Values are as they appear in AVU values.
    INCOMPLETE                = 'INCOMPLETE'
    COMPLETE                  = 'COMPLETE'
    UNPUBLISHED               = 'UNPUBLISHED'
    SUBMITTED_FOR_PUBLICATION = 'SUBMITTED_FOR_PUBLICATION'
    APPROVED_FOR_PUBLICATION  = 'APPROVED_FOR_PUBLICATION'
    PUBLISHED                 = 'PUBLISHED'
    PENDING_DEPUBLICATION     = 'PENDING_DEPUBLICATION'
    DEPUBLISHED               = 'DEPUBLISHED'
    PENDING_REPUBLICATION     = 'PENDING_REPUBLICATION'

    def __str__(self):
        return self.name


class research_package_state(Enum):
    """Research folder states."""

    # Values are as they appear in AVU values.
    FOLDER    = ''  # (absence of status attribute)
    LOCKED    = 'LOCKED'
    SUBMITTED = 'SUBMITTED'
    ACCEPTED  = 'ACCEPTED'
    REJECTED  = 'REJECTED'
    SECURED   = 'SECURED'

    def __str__(self):
        return self.name


# List of valid folder transitions (src, dst).
folder_transitions = [(research_package_state(x),
                       research_package_state(y))
                      for x, y in [('',          'LOCKED'),
                                   ('',          'SUBMITTED'),
                                   ('LOCKED',    ''),
                                   ('LOCKED',    'SUBMITTED'),
                                   ('SUBMITTED', ''),
                                   ('SUBMITTED', 'ACCEPTED'),
                                   ('SUBMITTED', 'REJECTED'),
                                   ('REJECTED',  'LOCKED'),
                                   ('REJECTED',  ''),
                                   ('REJECTED',  'SUBMITTED'),
                                   ('ACCEPTED',  'SECURED'),
                                   ('SECURED',   'LOCKED'),
                                   ('SECURED',   ''),
                                   ('SECURED',   'SUBMITTED')]]
