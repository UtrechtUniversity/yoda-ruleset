# -*- coding: utf-8 -*-
"""Functions for tape archive."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['api_tape_archive_stage',
           'api_tape_archive_state']


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


@api.make()
def api_tape_archive_stage(ctx, path):
    """Bring back a file from tape archive.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to file to bring back online from tape archive

    :returns: API status
    """
    return api.Result.ok()


@api.make()
def api_tape_archive_state(ctx, path):
    """Get the state of a file in the tape archive.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to file in the tape archive

    :returns: API status
    """
    return api.Result.ok()
