# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json

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
           'rule_vault_extract_archive']


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
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, "org_archival_status"),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return False


def vault_archive(ctx, actor, coll):
    try:
        # Prepare for archival.
        avu.set_on_coll(ctx, coll, "org_archival_status", "archive")
        provenance.log_action(ctx, actor, coll, "archive scheduled")

        # Send notifications to datamanagers.
        datamanagers = folder.get_datamanagers(ctx, coll)
        message = "Data package scheduled for archival"
        for datamanager in datamanagers:
            datamanager = '{}#{}'.format(*datamanager)
            notifications.set(ctx, actor, datamanager, coll, message)

        return "Success"

    except Exception:
        return "Failure"


def vault_create_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "archive":
        return "Invalid"
    try:
        avu.set_on_coll(ctx, coll, "org_archival_status", "archiving")

        collection.create(ctx, coll + "/archive")

        # create extra archive files
        system_metadata = package_system_metadata(ctx, coll)
        data_object.write(ctx, coll + "/archive/system-metadata.json",
                          jsonutil.dump(system_metadata))
        msi.data_obj_chksum(ctx, coll + "/archive/system-metadata.json", "", irods_types.BytesBuf())
        provenance_log = package_provenance_log(ctx, system_metadata)
        data_object.write(ctx, coll + "/archive/provenance-log.json",
                          jsonutil.dump(provenance_log))
        msi.data_obj_chksum(ctx, coll + "/archive/provenance-log.json", "", irods_types.BytesBuf())

        # copy/move existing data
        user_metadata = meta.get_latest_vault_metadata_path(ctx, coll)
        data_object.copy(ctx, user_metadata, coll + "/archive/user-metadata.json")
        data_object.copy(ctx, coll + "/License.txt", coll + "/archive/License.txt")
        collection.rename(ctx, coll + "/original", coll + "/archive/data")

        # create manifest
        data_object.write(ctx, coll + "/archive/manifest-sha256.txt",
                          package_manifest(ctx, coll + "/archive"))
        msi.data_obj_chksum(ctx, coll + "/archive/manifest-sha256.txt", "", irods_types.BytesBuf())

        ret = msi.archive_create(ctx, coll + "/archive.tar", coll + "/archive", TAPE_ARCHIVE_RESC, 0)
        if ret < 0:
            raise Exception("Archive creation failed: {}".format(ret))
        ctx.iiCopyACLsFromParent(coll + "/archive.tar", "default")
        ctx.dmput(package_archive_path(ctx, coll), "REG")
        collection.remove(ctx, coll + "/archive")

        avu.set_on_coll(ctx, coll, "org_archival_status", "archived")
        provenance.log_action(ctx, "system", coll, "archive completed")

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

        provenance.log_action(ctx, "system", coll, "archive failed")
        avu.set_on_coll(ctx, coll, "org_archival_status", "archival failed")

        return "Failure"


def vault_unarchive(ctx, actor, coll):
    try:
        # Prepare for unarchival.
        avu.set_on_coll(ctx, coll, "org_archival_status", "extract")
        provenance.log_action(ctx, actor, coll, "unarchive scheduled")

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
        avu.set_on_coll(ctx, coll, "org_archival_status", "extracting")

        ret = msi.archive_extract(ctx, coll + "/archive.tar", coll + "/archive", 0, 0, 0)
        if ret < 0:
            raise Exception("Archive extraction failed: {}".format(ret))
        collection.rename(ctx, coll + "/archive/data", coll + "/original")
        ctx.iiCopyACLsFromParent(coll + "/original", "recursive")
        collection.remove(ctx, coll + "/archive")
        data_object.remove(ctx, coll + "/archive.tar")

        avu.rm_from_coll(ctx, coll, "org_archival_status", "extracting")
        provenance.log_action(ctx, "system", coll, "unarchive completed")

        return "Success"
    except Exception:
        provenance.log_action(ctx, "system", coll, "unarchive failed")
        avu.set_on_coll(ctx, coll, "org_archival_status", "extraction failed")

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
