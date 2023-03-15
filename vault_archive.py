# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json
import time

import genquery
import irods_types

import folder
import groups
import meta
import notifications
import provenance
from util import *

__all__ = ['api_vault_archive',
           'api_vault_archival_status',
           'api_vault_extract',
           'rule_vault_archive',
           'rule_vault_create_archive',
           'rule_vault_extract_archive',
           'rule_vault_update_archive']


TAPE_ARCHIVE_RESC = "mockTapeArchive"


def package_manifest(ctx, coll):
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


def package_system_metadata(ctx, coll):
    """Retrieve system metadata of collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to retrieve system metadata of

    :returns: List of dicts with system metadata
    """
    return [
        {
            "name": row[0],
            "value": row[1]
        }
        for row in genquery.row_iterator(
            "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME like '{}%'".format(coll, constants.UUORGMETADATAPREFIX),
            genquery.AS_LIST,
            ctx)
    ]


def package_provenance_log(ctx, system_metadata):
    """Retrieve provenance log from system metadata.

    :param ctx:             Combined type of a callback and rei struct
    :param system_metadata: System metadata to retrieve provenance log from

    :returns: List of dicts with provenance log
    """
    def key(item):
        return int(item["time"])

    provenance_log = []
    for item in system_metadata:
        if item["name"] == constants.UUPROVENANCELOG:
            data = json.loads(item["value"])
            provenance_log.append({
                "time": data[0],
                "action": data[1],
                "actor": data[2]
            })
    return sorted(provenance_log, key=key)


def package_archive_path(ctx, coll):
    for row in genquery.row_iterator("DATA_PATH",
                                     "COLL_NAME = '{}' AND DATA_NAME = 'archive.tar'".format(coll),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]


def vault_archivable(ctx, coll):
    if not coll.endswith("/original"):
        for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                         "META_COLL_ATTR_NAME = 'org_vault_status' AND COLL_NAME = '{}'".format(coll),
                                         genquery.AS_LIST,
                                         ctx):
            return (collection.size(ctx, coll) >= int(config.data_package_limit))

    return False


def vault_archival_status(ctx, coll):
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.IIARCHIVEATTRNAME),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return False


def vault_archive(ctx, actor, coll):
    try:
        # Prepare for archival.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archive")
        provenance.log_action(ctx, actor, coll, "archive scheduled", False)

        # Send notifications to datamanagers.
        datamanagers = folder.get_datamanagers(ctx, coll)
        message = "Data package scheduled for archival"
        for datamanager in datamanagers:
            datamanager = '{}#{}'.format(*datamanager)
            notifications.set(ctx, actor, datamanager, coll, message)

        return "Success"

    except Exception:
        return "Failure"


def create_bagit_archive(ctx, archive, coll, resource, user_metadata, system_metadata, provenance_log):
    # create extra archive files
    data_object.copy(ctx, user_metadata, coll + "/user-metadata.json")
    data_object.write(ctx, coll + "/system-metadata.json",
                      jsonutil.dump(system_metadata))
    msi.data_obj_chksum(ctx, coll + "/system-metadata.json", "",
                        irods_types.BytesBuf())
    data_object.write(ctx, coll + "/provenance-log.json",
                      jsonutil.dump(provenance_log))
    msi.data_obj_chksum(ctx, coll + "/provenance-log.json", "",
                        irods_types.BytesBuf())

    # create manifest
    data_object.write(ctx, coll + "/manifest-sha256.txt",
                      package_manifest(ctx, coll))
    msi.data_obj_chksum(ctx, coll + "/manifest-sha256.txt", "",
                        irods_types.BytesBuf())

    # create archive
    ret = msi.archive_create(ctx, archive, coll, resource, 0)
    if ret < 0:
        raise Exception("Archive creation failed: {}".format(ret))


def extract_bagit_archive(ctx, archive, coll):
    path = pathutil.dirname(archive)
    while True:
        state = ctx.dmattr(package_archive_path(ctx, path), "", "")["arguments"][2]
        if state != "UNM":
            break
        time.sleep(1)
    if state != "DUL" and state != "REG" and state != "INV":
        raise Exception("Archive is not available")

    ret = msi.archive_extract(ctx, archive, coll, 0, 0, 0)
    if ret < 0:
        raise Exception("Archive extraction failed: {}".format(ret))


def vault_create_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "archive":
        return "Invalid"
    try:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archiving")
        collection.create(ctx, coll + "/archive")
        data_object.copy(ctx, coll + "/License.txt", coll + "/archive/License.txt")
        collection.rename(ctx, coll + "/original", coll + "/archive/data")

        system_metadata = package_system_metadata(ctx, coll)
        create_bagit_archive(ctx,
                             coll + "/archive.tar",
                             coll + "/archive",
                             TAPE_ARCHIVE_RESC,
                             meta.get_latest_vault_metadata_path(ctx, coll),
                             system_metadata,
                             package_provenance_log(ctx, system_metadata))
        ctx.iiCopyACLsFromParent(coll + "/archive.tar", "default")
        ctx.dmput(package_archive_path(ctx, coll), "", "REG")
        collection.remove(ctx, coll + "/archive")

        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archived")
        provenance.log_action(ctx, "system", coll, "archive completed", False)

        return "Success"
    except Exception:
        # attempt to restore package
        try:
            collection.rename(ctx, coll + "/archive/data", coll + "/original")
        except Exception:
            pass
        # remove temporary files
        try:
            collection.remove(ctx, coll + "/archive")
        except Exception:
            pass

        provenance.log_action(ctx, "system", coll, "archive failed", False)
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archival failed")

        return "Failure"


def vault_unarchive(ctx, actor, coll):
    try:
        # Prepare for unarchival.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extract")
        provenance.log_action(ctx, actor, coll, "unarchive scheduled", False)
        ctx.dmget(package_archive_path(ctx, coll), "", "OFL")

        # Send notifications to datamanagers.
        datamanagers = folder.get_datamanagers(ctx, coll)
        message = "Data package scheduled for unarchival"
        for datamanager in datamanagers:
            datamanager = '{}#{}'.format(*datamanager)
            notifications.set(ctx, actor, datamanager, coll, message)

        return "Success"

    except Exception:
        return "Failure"


def vault_extract_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "extract":
        return "Invalid"
    try:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extracting")

        extract_bagit_archive(ctx, coll + "/archive.tar", coll + "/archive")
        collection.rename(ctx, coll + "/archive/data", coll + "/original")
        ctx.iiCopyACLsFromParent(coll + "/original", "recursive")
        collection.remove(ctx, coll + "/archive")
        data_object.remove(ctx, coll + "/archive.tar")

        avu.rm_from_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extracting")
        provenance.log_action(ctx, "system", coll, "unarchive completed", False)

        return "Success"
    except Exception:
        provenance.log_action(ctx, "system", coll, "unarchive failed", False)
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extraction failed")

        return "Failure"


def update(ctx, coll, attr=None):
    if pathutil.info(coll)[0] == pathutil.Space.VAULT and attr != constants.IIARCHIVEATTRNAME and attr != constants.UUPROVENANCELOG and vault_archival_status(ctx, coll) == "archived":
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "update")
        ctx.dmget(package_archive_path(ctx, coll), "", "OFL")


def vault_update_archive(ctx, coll):
    try:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "updating")
        extract_bagit_archive(ctx, coll + "/archive.tar", coll + "/archive")
        data_object.remove(ctx, coll + "/archive.tar")

        system_metadata = package_system_metadata(ctx, coll)
        create_bagit_archive(ctx,
                             coll + "/archive.tar",
                             coll + "/archive",
                             TAPE_ARCHIVE_RESC,
                             meta.get_latest_vault_metadata_path(ctx, coll),
                             system_metadata,
                             package_provenance_log(ctx, system_metadata))
        ctx.iiCopyACLsFromParent(coll + "/archive.tar", "default")
        ctx.dmput(package_archive_path(ctx, coll), "", "REG")

        collection.remove(ctx, coll + "/archive")
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archived")
        return "Success"
    except Exception:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "update failed")
        return "Failure"


@api.make()
def api_vault_archive(ctx, coll):
    """Request to archive vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to archive

    :returns: API status
    """
    space, _, group, _ = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return "Invalid"
    category = groups.group_category(ctx, group)
    if not groups.user_is_datamanager(ctx, category, user.full_name(ctx)):
        return "Access denied"

    if not vault_archivable(ctx, coll) or vault_archival_status(ctx, coll):
        return "Invalid"

    try:
        ctx.iiAdminVaultArchive(coll)
        return "Success"
    except Exception:
        return "Failure"


@api.make()
def api_vault_archival_status(ctx, coll):
    """Request archival status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to request archive status from

    :returns: Vault data package archival status
    """
    return vault_archival_status(ctx, coll)


@api.make()
def api_vault_extract(ctx, coll):
    """Request to unarchive an archived vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to unarchive

    :returns: API status
    """
    space, _, group, _ = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return "Invalid"
    category = groups.group_category(ctx, group)
    if not groups.user_is_datamanager(ctx, category, user.full_name(ctx)):
        return "Access denied"

    if vault_archival_status(ctx, coll) != "archived":
        return "Invalid"

    try:
        ctx.iiAdminVaultArchive(coll)
        return "Success"
    except Exception:
        return "Failure"


@rule.make(inputs=[0, 1], outputs=[2])
def rule_vault_archive(ctx, actor, coll):
    if vault_archival_status(ctx, coll) == "archived":
        return vault_unarchive(ctx, actor, coll)

    return vault_archive(ctx, actor, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_create_archive(ctx, coll):
    return vault_create_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_extract_archive(ctx, coll):
    return vault_extract_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_update_archive(ctx, coll):
    return vault_update_archive(ctx, coll)
