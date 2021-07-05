# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import folder
from util import *

__all__ = ['api_deposit_path']

DEPOSIT_GROUP = "deposit-deposit"


def determine_deposit_path(ctx):
    """Determine deposit path for a user."""
    deposit_path = ""
    coll = "/" + user.zone(ctx) + "/home/" + DEPOSIT_GROUP
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '{}'".format(coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        deposit_path = row[0]

    if deposit_path == "":
        group = coll

        parts = group.split('-')
        base_name = '-'.join(parts[1:])

        parts = coll.split('/')
        datapackage_name = pathutil.basename(coll)

        if len(datapackage_name) > 235:
            datapackage_name = datapackage_name[0:235]

        ret = msi.get_icat_time(ctx, '', 'unix')
        timestamp = ret['arguments'][0].lstrip('0')

        # Ensure vault target does not exist.
        i = 0
        target_base = coll + "/" + datapackage_name + "[" + timestamp + "]"
        deposit_path = target_base
        while collection.exists(ctx, deposit_path):
            i += 1
            deposit_path = target_base + "[" + str(i) + "]"

        collection.create(ctx, deposit_path)

    return pathutil.basename(deposit_path)


@api.make()
def api_deposit_path(ctx):
    """Get deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to deposit collection
    """

    return {"deposit_path": determine_deposit_path(ctx)}


@api.make()
def api_deposit_submit(ctx):
    """Submit deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: API status
    """
    deposit_path = determine_deposit_path(ctx)
    coll = "/{}/home/{}".format(user.zone(ctx), deposit_path)

    return folder.set_status(ctx, coll, constants.research_package_state.SUBMITTED)
