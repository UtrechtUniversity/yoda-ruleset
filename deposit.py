# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

import folder
import meta
from util import *

__all__ = ['api_deposit_path',
           'api_deposit_status',
           'api_deposit_submit',
           'api_deposit_clear']

DEPOSIT_GROUP = "deposit-pilot"


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

    space, zone, group, subpath = pathutil.info(deposit_path)

    return "{}/{}".format(group, subpath)


@api.make()
def api_deposit_path(ctx):
    """Get deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to deposit collection
    """

    return {"deposit_path": determine_deposit_path(ctx)}


@api.make()
def api_deposit_status(ctx):
    """Retrieve status of deposit.

    :param ctx: Combined type of a callback and rei struct

    :returns: Deposit status
    """
    deposit_path = determine_deposit_path(ctx)
    coll = "/{}/home/{}".format(user.zone(ctx), deposit_path)
    meta_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    data = False
    if not collection.empty(ctx, coll):
        if collection.data_count(ctx, coll) == 1 and data_object.exists(ctx, meta_path):
            # Only file is yoda-metadata.json.
            data = False
        else:
            data = True

    metadata = False
    if data_object.exists(ctx, meta_path) and meta.is_json_metadata_valid(ctx, meta_path):
        metadata = True

    return {"data": data, "metadata": metadata}


@api.make()
def api_deposit_submit(ctx):
    """Submit deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: API status
    """
    deposit_path = determine_deposit_path(ctx)
    coll = "/{}/home/{}".format(user.zone(ctx), deposit_path)
    return folder.set_status(ctx, coll, constants.research_package_state.SUBMITTED)


@api.make()
def api_deposit_clear(ctx):
    """Clear deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: API status
    """
    deposit_path = determine_deposit_path(ctx)
    coll = "/{}/home/{}".format(user.zone(ctx), deposit_path)

    try:
        collection.remove(ctx, coll)
    except msi.Error:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()
