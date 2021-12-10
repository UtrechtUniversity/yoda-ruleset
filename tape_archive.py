# -*- coding: utf-8 -*-
"""Functions for tape archive."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['api_tape_archive_stage',
           'api_tape_archive_state']


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
    """Get the status of a file in the tape archive.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to file in the tape archive

    :returns: API status
    """
    return api.Result.ok()
