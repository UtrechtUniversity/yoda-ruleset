# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import irods_types

import notifications
import provenance
from util import *

__all__ = ['api_vault_download',
           'rule_vault_download',
           'rule_vault_download_archive']


def vault_downloadable(ctx, coll):
    if coll.endswith("/original"):
        return False
    for row in genquery.row_iterator("DATA_SIZE",
                                     "COLL_NAME = '{}' AND DATA_NAME = 'download.zip'".format(coll),
                                     genquery.AS_LIST,
                                     ctx):
        return False
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     "META_COLL_ATTR_NAME = 'org_vault_status' AND COLL_NAME = '{}'".format(coll),
                                     genquery.AS_LIST,
                                     ctx):
        return True

    return False


def vault_bagitor(ctx, coll):
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.IIBAGITOR),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return False


def vault_download(ctx, actor, coll):
    try:
        # Prepare for download.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "bagit")
        avu.set_on_coll(ctx, coll, constants.IIBAGITOR, actor)
        provenance.log_action(ctx, actor, coll, "download scheduled", False)

        return "Success"
    except Exception:
        return "Failure"


def vault_download_archive(ctx, coll):
    if bagit.status(ctx, coll) != "bagit":
        return "Invalid"
    try:
        actor = vault_bagitor(ctx, coll)
        avu.rm_from_coll(ctx, coll, constants.IIBAGITOR, actor)
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "baggingit")
        bagit.create(ctx, coll + "/download.zip", coll, 0)

        provenance.log_action(ctx, "system", coll, "creating download archive completed", False)
        avu.rm_from_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "baggingit")

        notifications.set(ctx, "system", actor, coll, "archive ready for download")
        log.write(ctx, "Archive of data package <{}> ready for download".format(coll))

        return "Success"
    except Exception:
        # remove bagit
        try:
            data_object.remove(ctx, coll + "/download.zip")
        except Exception:
            pass

        provenance.log_action(ctx, "system", coll, "creating download archive failed", False)
        avu.rm_from_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "baggingit")

        return "Failure"


@api.make()
def api_vault_download(ctx, coll):
    """Request to download a vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to download

    :returns: API status
    """
    if pathutil.info(coll).space != pathutil.Space.VAULT:
        return "Invalid"

    if not vault_downloadable(ctx, coll):
        return "Invalid"

    if bagit.status(ctx, coll):
        return "Invalid"

    try:
        ctx.iiAdminVaultArchive(coll, "download")
        return "Success"
    except Exception:
        return "Failure"


@rule.make(inputs=[0, 1], outputs=[2])
def rule_vault_download(ctx, actor, coll):
    return vault_download(ctx, actor, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_download_archive(ctx, coll):
    return vault_download_archive(ctx, coll)
