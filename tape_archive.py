# -*- coding: utf-8 -*-
"""Functions for tape archive."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import subprocess
from enum import Enum
from time import time

from util import *

__all__ = ['api_tape_archive_stage',
           'api_tape_archive_state']

DMGET = "/var/lib/irods/msiExecCmd_bin/dmget"
DMATTR = "/var/lib/irods/msiExecCmd_bin/dmattr"

TAPE_ARCHIVE_RESC = "mockTapeArchive"


class State(Enum):
    """DMF tape archive has several possible states for files."""

    REGULAR = "REG"
    """Regular. The file exists only online, on active disk."""

    OFFLINE = "OFL"
    """Offline. The file's directory entry remains on disk, but its data blocks are located offline only (on tape)."""

    DUAL_STATE = "DUL"
    """Dual-state. Identical copies of the file exist online (on disk) and offline (on tape).
    The online copy will persist if there is no demand for free space in its filesystem.
    When free space is needed, the online copy of the file is removed, leaving just the offline copy;
    the file becomes "offline." If you make any change to a dual-state file,
    the offline copy becomes out of date and invalid, and the file is once again a "regular" file."""

    MIGRATING = "MIG"
    """Migrating. The file is in process of migrating from disk to tape."""

    UNMIGRATING = "UNM"
    """Unmigrating. The file has been recalled and is in process of moving back from tape to disk."""

    NONMIGRATABLE = "NMG"
    """Nonmigratable. The file cannot be migrated."""

    INVALID = "INV"
    """Invalid. DMF cannot determine the file's state.
    The most likely reason is that it is in a filesystem that does not use DMF."""


def get_physical_path(ctx, path):
    """Get physical path of data object on tape archive."""
    coll_name, data_name = pathutil.chop(path)

    iter = genquery.row_iterator(
        "DATA_PATH",
        "RESC_NAME = '{}' AND COLL_NAME = '{}' AND DATA_NAME = '{}'".format(TAPE_ARCHIVE_RESC, coll_name, data_name),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


@api.make()
def api_tape_archive_stage(ctx, path):
    """Bring back a file from tape archive.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to file to bring back online from tape archive

    :returns: API status
    """
    physical_path = get_physical_path(ctx, path)

    if physical_path is None:
        return api.Error('file_not_found', 'Could not find file <{}> on tape archive resource'.format(path))

    dmget_command = "{} {}".format(DMGET, physical_path)
    process = subprocess.Popen(dmget_command.split(), stdout=subprocess.PIPE)
    _, error = process.communicate()

    if error is not None:
        return api.Error('dmget_failed', 'Request to bring file <{}> back online failed'.format(path))

    dmattr_command = "{} {}".format(DMATTR, physical_path)
    process = subprocess.Popen(dmattr_command.split(), stdout=subprocess.PIPE)
    state, error = process.communicate()

    if error is None:
        timestamp = int(time.time())
        avu.set_on_data(ctx, path, "org_tape_archive_time", timestamp)
        avu.set_on_data(ctx, path, "org_tape_archive_state", state)
    else:
        return api.Error('dmattr_failed', 'Retrieving file <{}> DMF state failed'.format(path))

    return api.Result.ok()


@api.make()
def api_tape_archive_state(ctx, path):
    """Get the state of a file in the tape archive.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to file in the tape archive

    :returns: API status
    """
    physical_path = get_physical_path(ctx, path)

    if physical_path is None:
        return api.Error('file_not_found', 'Could not find file <{}> on tape archive resource'.format(path))

    dmattr_command = "{} {}".format(DMATTR, physical_path)
    process = subprocess.Popen(dmattr_command.split(), stdout=subprocess.PIPE)
    state, error = process.communicate()

    if error is None:
        timestamp = int(time.time())
        avu.set_on_data(ctx, path, "org_tape_archive_time", timestamp)
        avu.set_on_data(ctx, path, "org_tape_archive_state", state)
        return state
    else:
        return api.Error('dmattr_failed', 'Retrieving file <{}> DMF state failed'.format(path))
