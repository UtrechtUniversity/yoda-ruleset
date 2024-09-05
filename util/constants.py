# -*- coding: utf-8 -*-
"""Constants that apply to all Yoda environments."""

__copyright__ = 'Copyright (c) 2016-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from enum import Enum

# TODO: Naming convention (no capitals, no UU/II prefix)
# TODO: dicts => enum.Enum
# TODO: all attrnames => one enum.Enum

IIGROUPPREFIX = "research-"
IIGRPPREFIX = "grp-"
IIVAULTPREFIX = "vault-"

UUORGMETADATAPREFIX = 'org_'
"""Prefix for organisational metadata."""

UUSYSTEMCOLLECTION = '/yoda'

UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION + '/revisions'
"""iRODS path where all revisions will be stored."""

PROC_REVISION_CLEANUP      = "revision-cleanup"
PROC_REVISION_CLEANUP_SCAN = "revision-cleanup-scan"
"""Process names of the revision cleanup jobs. Used by the spooling system"""

SPOOL_PROCESSES = {PROC_REVISION_CLEANUP, PROC_REVISION_CLEANUP_SCAN}
"""Set of process names recognized by the spooling system"""

SPOOL_MAIN_DIRECTORY = "/var/lib/irods/yoda-spool"
"""Directory that is used for storing Yoda batch process spool data on the provider"""

UUBLOCKLIST = ["._*", ".DS_Store"]
""" List of file extensions not to be copied to revision"""

UUMAXREVISIONSIZE = 2000000000
""" Max size of a file to be allowed to be made revisions
2GB as in 2 * 1000 * 1000 * 1000
"""

UUMETADATAGROUPSTORAGETOTALS = UUORGMETADATAPREFIX + 'storage_totals'
"""Metadata key for temporal total group storage (research, vault, revision)"""

UUPROVENANCELOG = UUORGMETADATAPREFIX + 'action_log'
"""Provenance log item."""

IILICENSECOLLECTION = UUSYSTEMCOLLECTION + '/licenses'
"""iRODS path where all licenses will be stored."""

IIPUBLICATIONCOLLECTION = UUSYSTEMCOLLECTION + '/publication'
"""iRODS path where publications will be stored. """

IITERMSCOLLECTION = UUSYSTEMCOLLECTION + "/terms"
"""iRODS path where the publication terms will be stored."""

IIJSONMETADATA = 'yoda-metadata.json'
"""Name of metadata JSON file."""

IIDATA_MAX_SLURP_SIZE = 4 * 1024 * 1024  # 4 MiB
"""The maximum file size that can be read into a string in memory, to prevent
   DOSing / out of control memory consumption."""

UUUSERMETADATAROOT = 'usr'
"""JSONAVU JSON root / namespace of user metadata (applied via JSON metadata file changes)."""

UUFLATINDEX = 'FlatIndex'
"""Flat unstructured index fields."""

IILOCKATTRNAME        = UUORGMETADATAPREFIX + 'lock'
IISTATUSATTRNAME      = UUORGMETADATAPREFIX + 'status'
IIVAULTSTATUSATTRNAME = UUORGMETADATAPREFIX + 'vault_status'
IIARCHIVEATTRNAME     = UUORGMETADATAPREFIX + 'archival_status'
IIBAGITOR             = UUORGMETADATAPREFIX + 'bagitor'
IICOPYPARAMSNAME      = UUORGMETADATAPREFIX + 'copy_to_vault_params'
IICOPYRETRYCOUNT      = UUORGMETADATAPREFIX + 'retry_count'
IICOPYLASTRUN         = UUORGMETADATAPREFIX + 'last_run'

DATA_PACKAGE_REFERENCE = UUORGMETADATAPREFIX + 'data_package_reference'

SCHEMA_USER_SELECTABLE = UUORGMETADATAPREFIX + 'schema_user_selectable'

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
    EMPTY                     = ''  # (absence of status attribute)
    INCOMPLETE                = 'INCOMPLETE'
    UNPUBLISHED               = 'UNPUBLISHED'
    SUBMITTED_FOR_PUBLICATION = 'SUBMITTED_FOR_PUBLICATION'
    APPROVED_FOR_PUBLICATION  = 'APPROVED_FOR_PUBLICATION'
    PUBLISHED                 = 'PUBLISHED'
    PENDING_DEPUBLICATION     = 'PENDING_DEPUBLICATION'
    DEPUBLISHED               = 'DEPUBLISHED'
    PENDING_REPUBLICATION     = 'PENDING_REPUBLICATION'

    def __str__(self):
        return self.name


# List of valid datapackage transitions (src, dst).
datapackage_transitions = [(vault_package_state(x),
                            vault_package_state(y))
                           for x, y in [('',                          'INCOMPLETE'),
                                        ('',                          'UNPUBLISHED'),
                                        ('INCOMPLETE',                'UNPUBLISHED'),
                                        ('UNPUBLISHED',               'SUBMITTED_FOR_PUBLICATION'),
                                        ('SUBMITTED_FOR_PUBLICATION', 'APPROVED_FOR_PUBLICATION'),
                                        ('SUBMITTED_FOR_PUBLICATION', 'UNPUBLISHED'),
                                        ('APPROVED_FOR_PUBLICATION',  'PUBLISHED'),
                                        ('PUBLISHED',                 'PENDING_DEPUBLICATION'),
                                        ('PENDING_DEPUBLICATION',     'DEPUBLISHED'),
                                        ('DEPUBLISHED',               'PENDING_REPUBLICATION'),
                                        ('PENDING_REPUBLICATION',     'PUBLISHED')]]


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
                                   ('ACCEPTED',  ''),
                                   # Backwards compatibility for folders that hold deprecated SECURED status.
                                   ('SECURED',   'LOCKED'),
                                   ('SECURED',   ''),
                                   ('SECURED',   'SUBMITTED')]]


# List of valid replica states.
class replica_status(Enum):
    STALE_REPLICA        = 0  # Replica is no longer known to be good
    GOOD_REPLICA         = 1  # Replica is good
    INTERMEDIATE_REPLICA = 2  # Replica is actively being written to
    READ_LOCKED          = 3  # Replica or a sibling replica is opened for read by an agent
    WRITE_LOCKED         = 4  # One of this replica's sibling replicas is actively being written to but is itself at rest


# List of valid automatic resource balancing (ARB) states
class arb_status(Enum):
    EXEMPT               = "EXEMPT"     # User has configured ruleset to not perform ARB for this resource
    IGNORE               = "IGNORE"     # ARB ignores this resource by design
    AVAILABLE            = "AVAILABLE"  # ARB applies to this resource. The resource has enough space available.
    FULL                 = "FULL"       # ARB applies to this resource. The resource does not have enough space available
