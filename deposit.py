# -*- coding: utf-8 -*-
"""Functions for deposit module."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import folder
import meta
from util import *

__all__ = ['api_deposit_create',
           'api_deposit_status',
           'api_deposit_submit']

DEPOSIT_GROUP = "deposit-pilot"


def determine_deposit_path(ctx):
    """Determine deposit path for a user."""
    coll = "/" + user.zone(ctx) + "/home/" + DEPOSIT_GROUP
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
def api_deposit_create(ctx):
    """Create deposit collection.

    :param ctx: Combined type of a callback and rei struct

    :returns: Path to created deposit collection
    """

    return {"deposit_path": determine_deposit_path(ctx)}


@api.make()
def api_deposit_status(ctx, path):
    """Retrieve status of deposit.

    :param ctx: Combined type of a callback and rei struct
    :param path: Path to deposit collection

    :returns: Deposit status
    """
    coll = "/{}/home{}".format(user.zone(ctx), path)
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
def api_deposit_submit(ctx, path):
    """Submit deposit collection.

    :param ctx: Combined type of a callback and rei struct
    :param path: Path to deposit collection

    :returns: API status
    """
    coll = "/{}/home{}".format(user.zone(ctx), path)
    return folder.set_status(ctx, coll, constants.research_package_state.SUBMITTED)
