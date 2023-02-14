# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import json

import genquery

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


def package_manifest(ctx, coll):
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
        provenance.log_action(ctx, actor, coll, "archive scheduled")

        user_metadata = meta.get_latest_vault_metadata_path(ctx, coll)
        ctx.msiDataObjCopy(user_metadata, coll + "/user-metadata.json", "verifyChksum=", 0)

        system_metadata = package_system_metadata(ctx, coll)
        data_object.write(ctx, coll + "/system-metadata.json",
                          jsonutil.dump(system_metadata))
        ctx.msiDataObjChksum(coll + "/system-metadata.json", "", "")

        provenance_log = package_provenance_log(ctx, system_metadata)
        data_object.write(ctx, coll + "/provenance-log.json",
                          jsonutil.dump(provenance_log))
        ctx.msiDataObjChksum(coll + "/provenance-log.json", "", "")

        data_object.write(ctx, coll + "/manifest-sha256.txt",
                          package_manifest(ctx, coll))
        ctx.msiDataObjChksum(coll + "/manifest-sha256.txt", "", "")

        # notify members of research group
        message = "Data package scheduled for archival"
        for row in genquery.row_iterator("COLL_ACCESS_USER_ID",
                                         "COLL_NAME = '{}'".format(coll),
                                         genquery.AS_LIST,
                                         ctx):
            id = row[0]
            for row2 in genquery.row_iterator("USER_NAME",
                                              "USER_ID = '{}'".format(id),
                                              genquery.AS_LIST,
                                              ctx):
                name = row2[0]
                if name.startswith("research-"):
                    for member in group.members(ctx, name):
                        member = '{}#{}'.format(*member)
                        notifications.set(ctx, actor, member, coll, message)

        # ready to be archived
        avu.set_on_coll(ctx, coll, "org_archival_status", "archive")

        return "Success"

    except Exception:
        return "Failure"


def vault_create_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "archive":
        return "Invalid"
    try:
        avu.set_on_coll(ctx, coll, "org_archival_status", "archiving")

        # move/copy files to a temporary collection to archive from
        ctx.msiCollCreate(coll + "/archive", "0", 0)
        ctx.msiDataObjRename(coll + "/user-metadata.json", coll + "/archive/user-metadata.json", "0", 0)
        ctx.msiDataObjRename(coll + "/system-metadata.json", coll + "/archive/system-metadata.json", "0", 0)
        ctx.msiDataObjRename(coll + "/provenance-log.json", coll + "/archive/provenance-log.json", "0", 0)
        ctx.msiDataObjRename(coll + "/manifest-sha256.txt", coll + "/archive/manifest-sha256.txt", "0", 0)
        ctx.msiDataObjRename(coll + "/original", coll + "/archive/original", "1", 0)
        ctx.msiDataObjCopy(coll + "/License.txt", coll + "/archive/License.txt", "verifyChksum=", 0)

        ctx.msiArchiveCreate(coll + "/archive.tar", coll + "/archive", 0, 0)
        ctx.iiCopyACLsFromParent(coll + "/archive.tar", "default")
        ctx.msiRmColl(coll + "/archive", "forceFlag=", 0)

        avu.set_on_coll(ctx, coll, "org_archival_status", "archived")
        provenance.log_action(ctx, "system", coll, "archive completed")

        return "Success"
    except Exception:
        # attempt to restore package
        try:
            ctx.msiDataObjRename(coll + "/archive/original", coll + "/original", "1", 0)
        except Exception:
            pass
        # remove temporary files
        try:
            ctx.msiRmColl(coll + "/archive", "forceFlag=", 0)
        except Exception:
            pass

        provenance.log_action(ctx, "system", coll, "archive failed")
        avu.set_on_coll(ctx, coll, "org_archival_status", "archival failed")

        return "Failure"


def vault_extract_archive(ctx, coll):
    if vault_archival_status(ctx, coll) != "extract":
        return "Invalid"
    try:
        avu.set_on_coll(ctx, coll, "org_archival_status", "extracting")

        ctx.msiArchiveExtract(coll + "/archive.tar", coll + "/archive", 0, 0, 0)
        ctx.msiDataObjRename(coll + "/archive/original", coll + "/original", "1", 0)
        ctx.iiCopyACLsFromParent(coll + "/original", "recursive")
        ctx.msiRmColl(coll + "/archive", "forceFlag=", 0)
        # ctx.msiDataObjUnlink("objPath=" + coll + "/archive.tar++++forceFlag=", 0)

        avu.rm_from_coll(ctx, coll, "org_archival_status", "extracting")
        provenance.log_action(ctx, actor, coll, "unarchive completed]")

        return "Success"
    except Exception:
        provenance.log_action(ctx, "system", coll, "unarchive failed")
        avu.set_on_coll(ctx, coll, "org_archival_status", "extraction failed")

        return "Failure"


@api.make()
def api_vault_archive(ctx, coll):
    if not vault_archivable(ctx, coll) or vault_archival_status(ctx, coll):
        return "Invalid"

    try:
        ctx.iiAdminVaultArchive(coll)
        return "Success"
    except Exception:
        return "Failure"


@api.make()
def api_vault_archival_status(ctx, coll):
    return vault_archival_status(ctx, coll)


@api.make()
def api_vault_extract(ctx, coll):
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
        provenance.log_action(ctx, actor, coll, "unarchive scheduled")
        avu.set_on_coll(ctx, coll, "org_archival_status", "extract")
        return "Success"

    return vault_archive(ctx, actor, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_create_archive(ctx, coll):
    return vault_create_archive(ctx, coll)


@rule.make(inputs=[0], outputs=[1])
def rule_vault_extract_archive(ctx, coll):
    return vault_extract_archive(ctx, coll)
