# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json
import time

import genquery
import irods_types

import constants
import data_object
import log
import msi


def manifest(ctx, coll):
    """Generate a BagIt manifest of collection.

    Manifest with a complete listing of each file name along with
    a corresponding checksum to permit data integrity checking.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to generate manifest of

    :returns: String with BagIt manifest
    """
    length = len(coll) + 1
    return "\n".join([
        data_object.decode_checksum(row[2]) + " " + (row[0] + "/" + row[1])[length:]
        for row in itertools.chain(
            genquery.row_iterator("COLL_NAME, ORDER(DATA_NAME), DATA_CHECKSUM",
                                  "COLL_NAME = '{}'".format(coll),
                                  genquery.AS_LIST,
                                  ctx),
            genquery.row_iterator("ORDER(COLL_NAME), ORDER(DATA_NAME), DATA_CHECKSUM",
                                  "COLL_NAME like '{}/%'".format(coll),
                                  genquery.AS_LIST,
                                  ctx))
        if row[0] != coll or not row[1].startswith("yoda-metadata")
    ]) + "\n"


def status(ctx, coll):
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.IIARCHIVEATTRNAME),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return False


def create(ctx, archive, coll, resource):
    # Create manifest file.
    log.write(ctx, "Creating manifest file for data package <{}>".format(coll))
    data_object.write(ctx, coll + "/manifest-sha256.txt", manifest(ctx, coll))
    msi.data_obj_chksum(ctx, coll + "/manifest-sha256.txt", "",
                        irods_types.BytesBuf())

    try:
    # Create archive.
        log.write(ctx, "Creating archive file for data package <{}>".format(coll))
        ret = msi.archive_create(ctx, archive, coll, resource, 0)
    except Exception:
        data_object.remove(ctx, coll + "/manifest-sha256.txt")
        pass

    # Remove manifest file.
    data_object.remove(ctx, coll + "/manifest-sha256.txt")

    if ret < 0:
        raise Exception("Archive creation failed: {}".format(ret))
    ctx.iiCopyACLsFromParent(archive, "default")


def extract(ctx, archive, coll):
    ret = msi.archive_extract(ctx, archive, coll, 0, 0, 0)
    if ret < 0:
        log.write(ctx, "Extracting archive of data package <{}> failed".format(coll))
        raise Exception("Archive extraction failed: {}".format(ret))
