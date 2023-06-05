# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

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
    minimum = int(config.data_package_archive_minimum)
    maximum = int(config.data_package_archive_maximum)

    # No archive limits configured.
    if minimum < 0 and maximum < 0:
        return True

    if not coll.endswith("/original"):
        for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                         "META_COLL_ATTR_NAME = 'org_vault_status' AND COLL_NAME = '{}'".format(coll),
                                         genquery.AS_LIST,
                                         ctx):
            coll_size = collection.size(ctx, coll)

            # Data package size is inside archive limits.
            if ((coll_size >= minimum and maximum < 0)
               or (minimum < 0 and coll_size <= maximum)
               or (coll_size >= minimum and coll_size <= maximum)):
                return True

    return False


def vault_archival_status(ctx, coll):
    return bagit.status(ctx, coll)


def create_archive(ctx, coll):
    log.write(ctx, "Creating archive of data package <{}>".format(coll))
    user_metadata = meta.get_latest_vault_metadata_path(ctx, coll)
    system_metadata = package_system_metadata(ctx, coll)
    provenance_log = package_provenance_log(ctx, system_metadata)

    # create extra archive files
    log.write(ctx, "Generating metadata for archive of data package <{}>".format(coll))
    data_object.copy(ctx, user_metadata, coll + "/archive/user-metadata.json")
    data_object.write(ctx, coll + "/archive/system-metadata.json",
                      jsonutil.dump(system_metadata))
    msi.data_obj_chksum(ctx, coll + "/archive/system-metadata.json", "",
                        irods_types.BytesBuf())
    data_object.write(ctx, coll + "/archive/provenance-log.json",
                      jsonutil.dump(provenance_log))
    msi.data_obj_chksum(ctx, coll + "/archive/provenance-log.json", "",
                        irods_types.BytesBuf())

    # create bagit archive
    bagit.create(ctx, coll + "/archive.tar", coll + "/archive", TAPE_ARCHIVE_RESC)
    msi.data_obj_chksum(ctx, coll + "/archive.tar", "", irods_types.BytesBuf())
    log.write(ctx, "Move archive of data package <{}> to tape".format(coll))
    ctx.dmput(package_archive_path(ctx, coll), config.data_package_archive_fqdn, "REG")


def extract_archive(ctx, coll):
    while True:
        state = ctx.dmattr(package_archive_path(ctx, coll), config.data_package_archive_fqdn, "")["arguments"][2]
        if state != "UNM" and state != "MIG":
            break
        time.sleep(10)

    if state != "DUL" and state != "REG" and state != "INV":
        log.write(ctx, "Archive of data package <{}> is not available, state is <{}>".format(coll, state))
        raise Exception("Archive is not available")

    bagit.extract(ctx, coll + "/archive.tar", coll + "/archive")


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

        log.write(ctx, "Data package <{}> scheduled for archving by <{}>".format(coll, actor))

        return "Success"

    except Exception:
        return "Failure"


def vault_create_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "archive":
        return "Invalid"
    try:
        log.write(ctx, "Start archival of data package <{}>".format(coll))
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archiving")
        collection.create(ctx, coll + "/archive")
        if data_object.exists(ctx, coll + "/License.txt"):
            data_object.copy(ctx, coll + "/License.txt", coll + "/archive/License.txt")
        collection.rename(ctx, coll + "/original", coll + "/archive/data")
        create_archive(ctx, coll)
        collection.remove(ctx, coll + "/archive")

        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archived")
        provenance.log_action(ctx, "system", coll, "archive completed", False)
        log.write(ctx, "Finished archival of data package <{}>".format(coll))

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
        log.write(ctx, "Archival of data package <{}> failed".format(coll))

        return "Failure"


def vault_unarchive(ctx, actor, coll):
    try:
        # Prepare for unarchival.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extract")
        provenance.log_action(ctx, actor, coll, "unarchive scheduled", False)
        log.write(ctx, "Request retrieval of data package <{}> from tape".format(coll))
        ctx.dmget(package_archive_path(ctx, coll), config.data_package_archive_fqdn, "OFL")

        # Send notifications to datamanagers.
        datamanagers = folder.get_datamanagers(ctx, coll)
        message = "Data package scheduled for unarchival"
        for datamanager in datamanagers:
            datamanager = '{}#{}'.format(*datamanager)
            notifications.set(ctx, actor, datamanager, coll, message)

        log.write(ctx, "Data package <{}> scheduled for unarchiving by <{}>".format(coll, actor))

        return "Success"

    except Exception:
        return "Failure"


def vault_extract_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "extract":
        return "Invalid"
    try:
        log.write(ctx, "Start unarchival of data package <{}>".format(coll))
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extracting")

        extract_archive(ctx, coll)
        collection.rename(ctx, coll + "/archive/data", coll + "/original")
        ctx.iiCopyACLsFromParent(coll + "/original", "recursive")
        collection.remove(ctx, coll + "/archive")
        data_object.remove(ctx, coll + "/archive.tar")

        avu.rm_from_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extracting")
        provenance.log_action(ctx, "system", coll, "unarchive completed", False)
        log.write(ctx, "Finished unarchival of data package <{}>".format(coll))

        return "Success"
    except Exception:
        provenance.log_action(ctx, "system", coll, "unarchive failed", False)
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extraction failed")
        log.write(ctx, "Unarchival of data package <{}> failed".format(coll))

        return "Failure"


def update(ctx, coll, attr):
    if pathutil.info(coll).space == pathutil.Space.VAULT and attr != constants.IIARCHIVEATTRNAME and attr != constants.UUPROVENANCELOG and vault_archival_status(ctx, coll) == "archived":
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "update")
        ctx.dmget(package_archive_path(ctx, coll), config.data_package_archive_fqdn, "OFL")


def vault_update_archive(ctx, coll):
    try:
        log.write(ctx, "Start update of archived data package <{}>".format(coll))
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "updating")

        extract_archive(ctx, coll)
        data_object.remove(ctx, coll + "/archive.tar")

        create_archive(ctx, coll)
        collection.remove(ctx, coll + "/archive")

        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "archived")
        log.write(ctx, "Finished update of archived data package <{}>".format(coll))
        return "Success"
    except Exception:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "update failed")
        log.write(ctx, "Update of archived data package <{}> failed".format(coll))

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
        ctx.iiAdminVaultArchive(coll, "archive")
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
        ctx.iiAdminVaultArchive(coll, "extract")
        return "Success"
    except Exception:
        return "Failure"


@rule.make(inputs=[0, 1, 2], outputs=[3])
def rule_vault_archive(ctx, actor, coll, action):
    if action == "archive":
        return vault_archive(ctx, actor, coll)
    elif action == "extract":
        return vault_unarchive(ctx, actor, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_create_archive(ctx, coll):
    return vault_create_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_extract_archive(ctx, coll):
    return vault_extract_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_update_archive(ctx, coll):
    return vault_update_archive(ctx, coll)
