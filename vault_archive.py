"""Functions to archive vault data packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2023-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64
import json
import time
from typing import List

import genquery
import irods_types
from tstrings import t

import folder
import groups
import meta
import notifications
import provenance
import vault
from util import *

__all__ = ['api_vault_archive',
           'api_vault_archival_status',
           'api_vault_extract',
           'rule_vault_archive',
           'rule_vault_create_archive',
           'rule_vault_extract_archive',
           'rule_vault_update_archive']


def package_system_metadata(ctx: rule.Context, coll: str) -> List:
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
            t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}%'"),
            genquery.AS_LIST,
            ctx)
    ]


def package_provenance_log(ctx: rule.Context, system_metadata: List) -> List:
    """Retrieve provenance log from system metadata.

    :param ctx:             Combined type of a callback and rei struct
    :param system_metadata: System metadata to retrieve provenance log from

    :returns: List of dicts with provenance log
    """
    def key(item: dict) -> int:
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


def package_archive_path(ctx: rule.Context, coll: str) -> str | None:
    for row in genquery.row_iterator("DATA_PATH",
                                     t("COLL_NAME = '{coll}' AND DATA_NAME = 'archive.tar'"),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]
    return None


def vault_archivable(ctx: rule.Context, coll: str) -> bool:
    minimum = int(config.data_package_archive_minimum)
    maximum = int(config.data_package_archive_maximum)

    # No archive limits configured.
    if minimum < 0 and maximum < 0:
        return True

    if not coll.endswith("/original"):
        for _row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                          t("META_COLL_ATTR_NAME = 'org_vault_status' AND COLL_NAME = '{coll}'"),
                                          genquery.AS_LIST,
                                          ctx):
            coll_size = collection.size(ctx, coll)

            # Data package size is inside archive limits.
            if ((coll_size >= minimum and maximum < 0)
               or (minimum < 0 and coll_size <= maximum)
               or (coll_size >= minimum and coll_size <= maximum)):
                return True

    return False


def vault_archival_status(ctx: rule.Context, coll: str) -> str | bool:
    for row in genquery.row_iterator("META_COLL_ATTR_VALUE",
                                     t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME = '{constants.IIARCHIVEATTRNAME}'"),
                                     genquery.AS_LIST,
                                     ctx):
        return row[0]

    return False


def create_archive(ctx: rule.Context, coll: str) -> None:
    log.write(ctx, f"Creating archive of data package <{coll}>")
    user_metadata = meta.get_latest_vault_metadata_path(ctx, coll)
    system_metadata = package_system_metadata(ctx, coll)
    provenance_log = package_provenance_log(ctx, system_metadata)

    # create extra archive files
    log.write(ctx, f"Generating metadata for archive of data package <{coll}>")
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
    bagit.create(ctx, coll + "/archive.tar", coll + "/archive", config.data_package_archive_resource)
    msi.data_obj_chksum(ctx, coll + "/archive.tar", "", irods_types.BytesBuf())
    log.write(ctx, f"Finished creating archive of data package <{coll}>, ready to move to tape")


def extract_archive(ctx: rule.Context, coll: str) -> None:
    while True:
        state = ctx.daattr(package_archive_path(ctx, coll), config.data_package_archive_fqdn, "")["arguments"][2]
        # File queued for staging from tape or being staged from tape.
        if state not in ("NA", "OFL", "QUE", "STG"):
            break
        time.sleep(10)

    if state not in ("DUL", "REG", "INV"):
        log.write(ctx, f"Archive of data package <{coll}> is not available, state is <{state}>")
        raise Exception("Archive is not available")

    bagit.extract(ctx, coll + "/archive.tar", coll + "/archive", resource=config.resource_vault)


def vault_archive(ctx: rule.Context, actor: str, coll: str) -> str:
    try:
        # Prepare for archival.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.ARCHIVE.value)
        provenance.log_action(ctx, actor, coll, "archive scheduled", False)

        # Send notifications to datamanagers.
        try:
            datamanagers = folder.get_datamanagers(ctx, coll)
        except ValueError as e:
            log.write(ctx, f"Unable to send vault archive notifications for <{coll}>: cannot get data managers: {str(e)}")
            datamanagers = []

        message = "Data package scheduled for archival"
        for datamanager in datamanagers:
            datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
            notifications.set(ctx, actor, datamanager_name, coll, message)

        log.write(ctx, f"Data package <{coll}> scheduled for archiving by <{actor}>")

        return "Success"

    except Exception:
        return "Failure"


def vault_create_archive(ctx: rule.Context, coll: str) -> str:
    if vault_archival_status(ctx, coll) != constants.vault_archive_state.ARCHIVE.value:
        return "Invalid"
    try:
        log.write(ctx, f"Start archival of data package <{coll}>")
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.ARCHIVING.value)
        collection.create(ctx, coll + "/archive")
        if data_object.exists(ctx, coll + "/License.txt"):
            data_object.copy(ctx, coll + "/License.txt", coll + "/archive/License.txt")
        collection.rename(ctx, coll + "/original", coll + "/archive/data")
        create_archive(ctx, coll)
        collection.remove(ctx, coll + "/archive", force=True)

        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.ARCHIVED.value)
        provenance.log_action(ctx, "system", coll, "archive completed", False)
        log.write(ctx, f"Finished archival of data package <{coll}>")

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
        log.write(ctx, f"Archival of data package <{coll}> failed")

        return "Failure"


def vault_unarchive(ctx: rule.Context, actor: str, coll: str) -> str:
    try:
        # Prepare for unarchival.
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.EXTRACT.value)
        provenance.log_action(ctx, actor, coll, "unarchive scheduled", False)
        log.write(ctx, f"Request retrieval of data package <{coll}> from tape")
        ctx.daget(package_archive_path(ctx, coll), config.data_package_archive_fqdn)

        # Send notifications to datamanagers.
        datamanagers = folder.get_datamanagers(ctx, coll)
        message = "Data package scheduled for unarchival"
        for datamanager in datamanagers:
            datamanager_name = f'{datamanager[0]}#{datamanager[1]}'
            notifications.set(ctx, actor, datamanager_name, coll, message)

        log.write(ctx, f"Data package <{coll}> scheduled for unarchiving by <{actor}>")

        return "Success"

    except Exception:
        return "Failure"


def vault_extract_archive(ctx: rule.Context, coll: str) -> str:
    if vault_archival_status(ctx, coll) != constants.vault_archive_state.EXTRACT.value:
        return "Invalid"
    try:
        log.write(ctx, f"Start unarchival of data package <{coll}>")
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.EXTRACTING.value)

        extract_archive(ctx, coll)
        collection.rename(ctx, coll + "/archive/data", coll + "/original")
        vault.copy_acls_from_parent(ctx, coll + "/original", "recursive")
        collection.remove(ctx, coll + "/archive", force=True)
        data_object.remove(ctx, coll + "/archive.tar", force=True)

        avu.rm_from_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.EXTRACTING.value)
        provenance.log_action(ctx, "system", coll, "unarchive completed", False)
        log.write(ctx, f"Finished unarchival of data package <{coll}>")

        return "Success"
    except Exception:
        provenance.log_action(ctx, "system", coll, "unarchive failed", False)
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "extraction failed")
        log.write(ctx, f"Unarchival of data package <{coll}> failed")

        return "Failure"


def update(ctx: rule.Context, coll: str, attr: str | None) -> None:
    if (pathutil.info(coll).space == pathutil.Space.VAULT
       and attr not in (constants.IIARCHIVEATTRNAME, constants.UUPROVENANCELOG)
       and vault_archival_status(ctx, coll) == constants.vault_archive_state.ARCHIVED.value):
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.UPDATE.value)
        ctx.daget(package_archive_path(ctx, coll), config.data_package_archive_fqdn)


def vault_update_archive(ctx: rule.Context, coll: str) -> str:
    try:
        log.write(ctx, f"Start update of archived data package <{coll}>")
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.UPDATING.value)

        extract_archive(ctx, coll)
        data_object.remove(ctx, coll + "/archive.tar", force=True)

        create_archive(ctx, coll)
        collection.remove(ctx, coll + "/archive", force=True)

        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, constants.vault_archive_state.ARCHIVED.value)
        log.write(ctx, f"Finished update of archived data package <{coll}>")
        return "Success"
    except Exception:
        avu.set_on_coll(ctx, coll, constants.IIARCHIVEATTRNAME, "update failed")
        log.write(ctx, f"Update of archived data package <{coll}> failed")

        return "Failure"


@api.make()
def api_vault_archive(ctx: rule.Context, coll: str) -> api.Result:
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

    # Encode paths into base64
    encoded_coll = base64.b64encode(coll.encode()).decode()

    try:
        ctx.iiAdminVaultArchive(encoded_coll, constants.vault_archive_state.ARCHIVE.value)
        return "Success"
    except Exception:
        return "Failure"


@api.make()
def api_vault_archival_status(ctx: rule.Context, coll: str) -> api.Result:
    """Request archival status of vault data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of vault data package to request archive status from

    :returns: Vault data package archival status
    """
    return vault_archival_status(ctx, coll)


@api.make()
def api_vault_extract(ctx: rule.Context, coll: str) -> api.Result:
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

    if vault_archival_status(ctx, coll) != constants.vault_archive_state.ARCHIVED.value:
        return "Invalid"

    # Encode paths into base64
    encoded_coll = base64.b64encode(coll.encode()).decode()

    try:
        ctx.iiAdminVaultArchive(encoded_coll, constants.vault_archive_state.EXTRACT.value)
        return "Success"
    except Exception:
        return "Failure"


@rule.make(inputs=[0, 1, 2, 3], outputs=[3])
def rule_vault_archive(ctx: rule.Context, actor: str, coll: str, action: str, status: str) -> str:
    # Decode base64-encoded paths
    try:
        decoded_coll = base64.b64decode(coll).decode('utf-8')
    except Exception as e:
        log.write(ctx, f"Failed to decode base64-encoded path '{coll}' for archive: {str(e)}")
        return "Failure"

    if not decoded_coll or not decoded_coll.startswith('/'):
        log.write(ctx, f"Invalid path after decoding for archive: <{decoded_coll}>")
        return "Failure"

    log.write(ctx, f"vault_archive: {actor} {action} '{decoded_coll}' (status: {status})")

    if action == "archive":
        return vault_archive(ctx, actor, decoded_coll)
    elif action == "extract":
        return vault_unarchive(ctx, actor, decoded_coll)
    else:
        return "Failure"


@rule.make(inputs=[0], outputs=[1])
def rule_vault_create_archive(ctx: rule.Context, coll: str) -> str:
    return vault_create_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_extract_archive(ctx: rule.Context, coll: str) -> str:
    return vault_extract_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_update_archive(ctx: rule.Context, coll: str) -> str:
    return vault_update_archive(ctx, coll)
