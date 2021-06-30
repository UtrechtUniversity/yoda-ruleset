# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from folder import set_status
from util import *

__all__ = ['api_deposit_path']


@api.make()
def api_deposit_path(ctx):
    """Get deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to deposit collection
    """
    return {"deposit_path": "research-initial"}


@api.make()
def api_deposit_submit(ctx):
    """Submit deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: API status
    """
    deposit_path = "research-initial"
    coll = "/{}/home{}".format(user.zone(ctx), deposit_path)

    return set_status(ctx, coll, constants.research_package_state.SUBMITTED)
