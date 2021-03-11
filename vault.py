# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import os
import time
from datetime import datetime

import irods_types

import folder
import group
import intake_lock
import intake_scan
import mail
import meta
import meta_form
import policies_datapackage_status
from util import *


__all__ = ['api_vault_submit',
           'api_vault_approve',
           'api_vault_cancel',
           'api_vault_depublish',
           'api_vault_republish',
           'api_vault_preservable_formats_lists',
           'api_vault_unpreservable_files',
           'rule_vault_copy_original_metadata_to_vault',
           'rule_vault_write_license',
           'rule_vault_process_status_transitions',
           'api_vault_system_metadata',
           'api_vault_collection_details',
           'api_vault_copy_to_research',
           'api_vault_get_publication_terms',
           'rule_intake_to_vault']


@rule.make(inputs=range(2), outputs=range(2, 2))
def rule_intake_to_vault(ctx, intake_root, vault_root):
    log.write(ctx, intake_root)

    # 1. add to_vault_freeze metadata lock to the dataset
    # 2. check that dataset does not yet exist in the vault
    # 3. copy dataset to vault with its metadata
    # 4. remove dataset from intake
    # upon any error:
    # - delete partial data from vault
    # - add error to intake dataset metadata
    # - remove locks on intake dataset (to_vault_freeze, to_vault_lock)

    # note that we have to allow for multiple types of datasets:
    #    type A: a single toplevel collection with a tree underneath
    #    type B: one or more datafiles located within the same collection
    # processing varies slightly between them, so process each type in turn
    #

    # status: 0 is success, nonzero is error
    status = 0
    # counter of datasets moved to the vault area
    datasets_moved = 0

    # TYPE A:
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '" + intake_root + "%'",
        genquery.AS_LIST, ctx)

    for row in iter:
        toplevel_collection = row[0]
        dataset_id = row[1]
        # Find locked/fronzen status
        locked_state = intake_scan.object_is_locked(ctx, toplevel_collection, True)
        if locked_state['locked']:
            # Freeze the dataset
            intake_lock.intake_dataset_freeze(ctx, toplevel_collection, dataset_id)

            # Dataset frozen, now move to vault and remove from intake area
            status = dataset_collection_move_2_vault(ctx, intake_root, toplevel_collection, dataset_id, vault_root)
            if status == 0:
                datasets_moved += 1

    # TYPE B:
    iter = genquery.row_iterator(
        "COLL_NAME, META_DATA_ATTR_VALUE",
        "META_DATA_ATTR_NAME = 'dataset_toplevel' AND COLL_NAME like '" + intake_root + "%'",
        genquery.AS_LIST, ctx)

    for row in iter:
        toplevel_collection = row[0]
        dataset_id = row[1]
        # check if to_vault_lock exists on all the dataobjects of this dataset
        all_locked = True

        iter2 = genquery.row_iterator(
            "DATA_NAME",
            "COLL_NAME = '" + toplevel_collection + "' "
            "AND META_DATA_ATTR_NAME = 'dataset_toplevel' "
            "AND META_DATA_ATTR_VALUE = '" + dataset_id + "'",
            genquery.AS_LIST, ctx)

        for row2 in iter2:
            locked_state = intake_scan.object_is_locked(ctx, toplevel_collection + '/' + row2[0], False)
            all_locked = all_locked and locked_state['locked']
            if not all_locked:
                break

        if all_locked:
            # Freeze the dataset
            intake_lock.intake_dataset_freeze(ctx, toplevel_collection, dataset_id)

            # Dataset frozen, now move to fault and remove from intake area
            status = dataset_objects_only_move_2_vault(ctx, intake_root, toplevel_collection, dataset_id, vault_root)
            if status == 0:
                datasets_moved += 1

    if datasets_moved:
        log.write(ctx, "Datasets moved to the vault: " + str(datasets_moved))

    return 0


def dataset_collection_move_2_vault(ctx, intake_root, toplevel_collection, dataset_id, vault_root):
    """Move intake datasets consisting of collections to the vault

    :param ctx:           Combined type of a callback and rei struct

    :return status
    """
    status = 0
    if vault_dataset_exists(ctx, vault_root, dataset_id):
        # duplicate dataset, signal error and throw out of vault queue
        log.write(ctx, "INFO: version already exists in vault: " + dataset_id)
        message = "Duplicate dataset, version already exists in vault"
        intake_scan.dataset_add_error(ctx, [toplevel_collection], True, message)
        intake_lock.intake_dataset_melt(ctx, toplevel_collection, dataset_id)
        intake_lock.intake_dataset_unlock(ctx, toplevel_collection, dataset_id)
        return 1

    # Dataset does not exist - move from research to vault area
    vault_path = get_dataset_path(vault_root, dataset_id)

    vault_parent = pathutil.chop(vault_path)[0]
    try:
        collection.create(ctx, vault_parent, "1")
    except Exception as e:
        log.write(ctx, "ERROR: parent collection could not be created " + vault_parent)
        return 2

    # variable for treewalk interface
    buffer = {}
    buffer["source"] = toplevel_collection
    buffer["destination"] = vault_path

    status = vault_tree_walk_collection(ctx, toplevel_collection, buffer, vault_walk_ingest_object)

    # reset buffer
    buffer = {}
    if status == 0:
        # stamip the vault dataset collection with additional metadata
        date_created = datetime.now()
        avu.add_to_coll(ctx, vault_path, "dataset_date_created", date_created.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))

        # and finally remove the dataset original in the intake area
        try:
            collection.remove(ctx, toplevel_collection)
        except Exception as e:
            log.write(ctx, "ERROR: unable to remove intake collection " + toplevel_collection)
            return 3
    else:
        # move failed (partially), cleanup vault
        # NB: keep the dataset in the vault queue so we can retry some other time
        log.write("ERROR: Ingest failed for " + dataset_id + ", error = " + status)
        status = vault_tree_walk_collection(ctx, vault_path, buffer, vault_walk_remove_object)

    return status


def dataset_objects_only_move_2_vault(ctx, intake_root, toplevel_collection, dataset_id, vault_root):
    """Move intake datasets consisting of data objects to the vault
    :param ctx:           Combined type of a callback and rei struct

    return status
    """
    status = 0
    if vault_dataset_exists(ctx, vault_root, dataset_id):
        # duplicate dataset, signal error and throw out of vault queue
        log.write(ctx, "INFO: version already exists in vault: " + dataset_id)
        message = "Duplicate dataset, version already exists in vault"
        intake_scan.dataset_add_error(ctx, [toplevel_collection], True, message)
        intake_lock.intake_dataset_melt(ctx, toplevel_collection, dataset_id)
        intake_lock.intake_dataset_unlock(ctx, toplevel_collection, dataset_id)
        return 1

    # Dataset does not exist - move it from research to vault space
    # new dataset(version) we can safely ingest into vault
    vault_path = get_dataset_path(vault_root, dataset_id)

    # create path to and including the toplevel collection (will create in-between levels)
    try:
        collection.create(ctx, vault_path)
    except Exception as e:
        log.write(ctx, "ERROR: parent collection could not be created " + vault_path)
        return 2

    # stamp the vault dataset collection with default metadata
    try:
        vault_dataset_add_default_metadata(ctx, vault_path, dataset_id)
    except Exception as e:
        log.write(ctx, "ERROR: default metadata could not be added to " + vault_path)
        return 3

    # copy data objects to the vault
    iter = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME = '" + topLevel_collection + "' "
        "AND META_DATA_ATTR_NAME = 'dataset_toplevel' "
        "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
        genquery.AS_LIST, ctx)

    for row in iter:
        intake_path = toplevel_collection + '/' + row[0]

        status = vault_ingest_object(ctx, intake_path, False, vault_path + "/" + row[0])
        if status:
            break

        # data ingested, what's left is to delete the original in intake area
        # this will also melt/unfreeze etc because metadata is removed too
        iter = genquery.row_iterator(
            "DATA_NAME",
            "COLL_NAME = '" + topLevel_collection + "' "
            "AND META_DATA_ATTR_NAME = 'dataset_toplevel' "
            "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            intake_path = topLevel_collection + "/" + row[0]
            # Now remove data object in intake
            try:
                data_object.remove(ctx, intake_path)
            except Exception as e:
                log.write(ctx, "ERROR: unable to remove intake object " + intake_path)
                # error occurred during ingest, cleanup vault area and relay the error to user
                # NB: keep the dataset in the vault queue so we can retry some other time
                log.write(ctx, "ERROR: Ingest failed for *datasetId error = *status")

                # reset buffer interface
                buffer = {}
                status = vault_tree_walk_collection(ctx, vault_path, buffer, vault_walk_remove_object)

    # Finally return status
    return status


def vault_ingest_object(ctx, object_path, is_collection, vault_path):
    # from the original object only the below list is copied to the vault object, other info is ignored
    copied_metadata = ["wave", "experiment_type", "pseudocode", "version",
                       "error", "warning", "comment", "dataset_error",
                       "dataset_warning", "datasetid"]

    if not is_collection:
        # first chksum the orginal file then use it to verify the vault copy
        try:
            ctx.msiDataObjChksum(object_path, "forceChksum=", 0)
            ctx.msiDataObjCopy(object_path, vault_path, 'verifyChksum=', 0)
        except msi.Error as e:
            return 1

        coll, dataname = pathutil.chop(object_path)

        iter = genquery.row_iterator(
            "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE",
            "COLL_NAME = '" + coll + "' AND DATA_NAME = '" + dataname + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            if row[0] in copied_metadata:
                avu.set_on_data(ctx, vault_path, row[0], row[1])

        # add metadata found in system info
        iter = genquery.row_iterator(
            "DATA_OWNER_NAME, DATA_OWNER_ZONE, DATA_CREATE_TIME",
            "COLL_NAME = '" + coll + "' AND DATA_NAME = '" + dataname + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            avu.set_on_data(ctx, vault_path, "submitted_by=", row[0] + '#' + row[1])
            avu.set_on_data(ctx, vault_path, "submitted_date", row[2])
    else:
        # CREATE COLLECTION
        try:
            collection.create(ctx, vault_path, "1")
        except msi.Error as e:
            return 1

        iter = genquery.row_iterator(
            "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + object_path + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            if row[0] in copied_metadata:
                avu.set_on_coll(ctx, vault_path, row[0], row[1])

        # add metadata found in system info
        iter = genquery.row_iterator(
            "COLL_OWNER_NAME, COLL_OWNER_ZONE, COLL_CREATE_TIME",
            "COLL_NAME = '" + object_path + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            avu.set_on_coll(ctx, vault_path, "submitted_by=", row[0] + '#' + row[1])
            avu.set_on_coll(ctx, vault_path, "submitted_date", row[2])

    return 0


def vault_walk_remove_object(ctx, item_parent, item_name, is_collection):
    status = 0
    try:
        if is_collection:
            collection.remove(ctx, item_parent + '/' + item_name)
        else:
            data_object.remove(ctx, item_parent + '/' + item_name)
    except Exception as e:
        status = 1

    return status


def vault_walk_ingest_object(ctx, item_parent, item_name, is_collection, buffer):
    source_path = item_parent + '/' + item_name
    dest_path = buffer["destination"]
    if source_path != buffer["source"]:
        # rewrite path to copy objects that are located underneath the toplevel collection
        source_length = len(source_path)
        relative_path = source_path[(len(buffer["source"]) + 1): source_length]
        dest_path = buffer["destination"] + '/' + relative_path

    return vault_ingest_object(ctx, source_path, is_collection, dest_path)


def vault_tree_walk_collection(ctx, path, buffer, rule_to_process):
    """
    Walk a subtree and perfom 'rule_to_process' per item.

    :param path
    :param buffer            (exclusively to be used by the rule we will can)
    :param rule_to_process   name of the rule to be executed in the context of a tree-item
    """
    parent_collection, collection = pathutil.chop(path)

    error = 0
    # first deal with any subcollections within this collection
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '" + path + "' ",
        genquery.AS_LIST, ctx)
    for row in iter:
        error = vault_tree_walk_collection(ctx, row[0], buffer, rule_to_process)
        if error:
            break

    # when done then process the dataobjects directly located within this collection
    if error == 0:
        iter = genquery.row_iterator(
            "DATA_NAME",
            "COLL_NAME = '" + path + "' ",
            genquery.AS_LIST, ctx)
        for row in iter:
            error = rule_to_process(ctx, path, row[0], False, buffer)
            if error:
                break

    # and lastly process the collection itself
    if error == 0:
        error = rule_to_process(ctx, parent_collection, collection, True, buffer)

    return error


def vault_dataset_add_default_metadata(ctx, vault_path, dataset_id):
    id_components = intake_scan.dataset_parse_id(dataset_id)
    my_date = datetime.now()
    id_components["dataset_date_created"] = my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

    keys = ["wave", "experiment_type", "pseudocode", "version", "dataset_date_created"]
    for key in keys:
        # ??? Dit kan ook een collection zijn!
        avu.set_on_data(ctx, vault_path, key, id_components[key])


def vault_dataset_exists(ctx, vault_root, dataset_id):
    id_components = intake_scan.dataset_parse_id(dataset_id)
    # Beware! extra 'ver' before version from orginal code: *wepv = *wave ++ *sep ++ *experimentType ++ *sep ++ *pseudocode ++ *sep ++ "ver*version";
    wepv = id_components["wave"] + "_" + id_components["experiment_type"] + "_" + id_components["pseudocode"] + "_ver" + id_components["version"]
    dataset_path = vault_root + '/' + id_components["wave"] + "/" + id_components["experiment_type"] + "/" + id_components["pseudocode"] + "/" + wepv

    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME = '" + dataset_path + "' ",
        genquery.AS_LIST, ctx)

    for row in iter:
        return True
    return False


def get_dataset_path(root, dataset_id):
    id_components = intake_scan.dataset_parse_id(dataset_id)
    # Beware! extra 'ver' before version from orginal code: *wepv = *wave ++ *sep ++ *experimentType ++ *sep ++ *pseudocode ++ *sep ++ "ver*version";
    wepv = id_components["wave"] + "_" + id_components["experiment_type"] + "_" + id_components["pseudocode"] + "_ver" + id_components["version"]

    return root + '/' + id_components["wave"] + "/" + id_components["experiment_type"] + "/" + id_components["pseudocode"] + "/" + wepv


api.make()
def api_vault_submit(ctx, coll):
    """Submit data package for publication.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to submit

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.SUBMITTED_FOR_PUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_approve(ctx, coll):
    """Approve data package for publication.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to approve

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.APPROVED_FOR_PUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_cancel(ctx, coll):
    """Cancel submit of data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to cancel submit

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.UNPUBLISHED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_depublish(ctx, coll):
    """Depublish data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to depublish

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.PENDING_DEPUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_republish(ctx, coll):
    """Republish data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to republish

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.PENDING_REPUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_copy_to_research(ctx, coll_origin, coll_target):
    """Copy data package from vault to research space.

    :param ctx:         Combined type of a callback and rei struct
    :param coll_origin: Collection of data package to copy
    :param coll_target: Collection to copy data package to

    :returns: API status
    """
    zone = user.zone(ctx)

    # API error introduces post-error in requesting application.
    if coll_target == "/" + zone + "/home":
        return api.Error('HomeCollectionNotAllowed', 'Please select a specific research folder for your datapackage', {"bla": "bla", "bla2": "bla2bla2"})

    # Check if target is a research folder. I.e. none-vault folder.
    parts = coll_target.split('/')
    group_name = parts[3]
    if group_name.startswith('vault-'):
        return api.Error('RequiredIsResearchArea', 'Please select a specific research folder for your datapackage')

    # Check whether datapackage folder already present in target folder.
    # Get package name from origin path
    parts = coll_origin.split('/')
    new_package_collection = coll_target + '/' + parts[-1]

    # Now check whether target collection already exist.
    if collection.exists(ctx, new_package_collection):
        return api.Error('PackageAlreadyPresentInTarget', 'This datapackage is already present at the specified place')

    # Check if target path exists.
    if not collection.exists(ctx, coll_target):
        return api.Error('TargetPathNotExists', 'The target you specified does not exist')

    # Check if user has READ ACCESS to specific vault packatge in collection coll_origin.
    user_full_name = user.full_name(ctx)
    category = meta_form.group_category(ctx, group_name)
    is_datamanager = meta_form.user_is_datamanager(ctx, category, user.full_name(ctx))

    if not is_datamanager:
        # Check if research group has access by checking of research-group exists for this user.
        research_group_access = collection.exists(ctx, '/' + parts[0] + '/' + parts[1] + '/' + parts[2])

        if not research_group_access:
            return api.Error('NoPermissions', 'Insufficient rights to perform this action')

    # Check for possible locks on target collection.
    lock_count = meta_form.get_coll_lock_count(ctx, coll_target)
    if lock_count:
        return api.Error('TargetCollectionLocked', 'The folder you selected is locked.')

    # Check if user has write access to research folder.
    # Only normal user has write access.
    if not meta_form.user_member_type(ctx, group_name, user_full_name) in ['normal', 'manager']:
        return api.Error('NoWriteAccessTargetCollection', 'Not permitted to write in selected folder')

    # Register to delayed rule queue.
    delay = 10

    ctx.delayExec(
        "<PLUSET>%ds</PLUSET>" % delay,
        "iiCopyFolderToResearch('%s', '%s')" % (coll_origin, coll_target),
        "")

    # TODO: response nog veranderen
    return {"status": "ok",
            "target": coll_target,
            "origin": coll_origin}


@api.make()
def api_vault_preservable_formats_lists(ctx):
    """Retrieve lists of preservable file formats on the system.

    :param ctx: Combined type of a callback and rei struct

    :returns: dict -- Lists of preservable file formats {name => [ext...]}
    """
    zone = user.zone(ctx)

    # Retrieve all preservable file formats lists on the system.

    files = [x for x in collection.data_objects(ctx, '/{}/yoda/file_formats'.format(zone))
             if x.endswith('.json')]

    # Return dict of list filename (without extension) -> JSON contents
    return {os.path.splitext(pathutil.chop(x)[1])[0]:
            jsonutil.read(ctx, x) for x in files}


@api.make()
def api_vault_unpreservable_files(ctx, coll, list_name):
    """Retrieve the set of unpreservable file formats in a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param coll:      Collection of folder to check
    :param list_name: Name of preservable file format list

    :returns: Set of unpreservable file formats
    """
    zone = pathutil.info(coll)[1]

    # Retrieve JSON list of preservable file formats.
    list_data = jsonutil.read(ctx, '/{}/yoda/file_formats/{}.json'.format(zone, list_name))
    preservable_formats = set(list_data['formats'])

    # Get basenames of all data objects within this collection.
    data_names = itertools.imap(lambda x: pathutil.chop(x)[1],
                                collection.data_objects(ctx, coll, recursive=True))

    # If JSON is considered unpreservable, ignore yoda-metadata.json.
    data_names = itertools.ifilter(lambda x: x != constants.IIJSONMETADATA, data_names)

    # Data names -> lowercase extensions, without the dot.
    exts  = set(list(itertools.imap(lambda x: os.path.splitext(x)[1][1:].lower(), data_names)))
    exts -= set([''])

    # Return any ext that is not in the preservable list.
    return list(exts - preservable_formats)


def rule_vault_copy_original_metadata_to_vault(rule_args, callback, rei):
    """Copy the original metadata JSON into the root of the package.

    :param rule_args: [0] Path of a new package in the vault
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
    """
    vault_package = rule_args[0]
    vault_copy_original_metadata_to_vault(callback, vault_package)


def vault_copy_original_metadata_to_vault(ctx, vault_package_path):
    """Copy original metadata to the vault package root.

    :param ctx:  Combined type of a callback and rei struct
    :param vault_package_path: Path of a package in the vault
    """
    original_metadata = vault_package_path + "/original/" + constants.IIJSONMETADATA
    copied_metadata = vault_package_path + '/yoda-metadata[' + str(int(time.time())) + '].json'

    # Copy original metadata JSON.
    ctx.msiDataObjCopy(original_metadata, copied_metadata, 'verifyChksum=', 0)
    # msi.data_obj_copy(ctx, original_metadata, copied_metadata, 'verifyChksum=', irods_types.BytesBuf())


def rule_vault_write_license(rule_args, callback, rei):
    """Write the license as a text file into the root of the vault package.

    :param rule_args: [0] Path of a package in the vault
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
    """

    vault_pkg_coll = rule_args[0]
    vault_write_license(callback, vault_pkg_coll)


def vault_write_license(ctx, vault_pkg_coll):
    """Write the license as a text file into the root of the vault package.

    :param ctx:  Combined type of a callback and rei struct
    :param vault_pkg_coll: Path of a package in the vault
    """
    zone = user.zone(ctx)

    # Retrieve license.
    license = ""
    license_key = "License"
    license_unit = "{}_%".format(constants.UUUSERMETADATAROOT)

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_UNITS LIKE '{}'".format(vault_pkg_coll, license_key, license_unit),
        genquery.AS_LIST, ctx)

    for row in iter:
        license = row[0]

    if license == "":
        # No license set in user metadata.
        log.write(ctx, "rule_vault_write_license: No license found in user metadata <{}>".format(vault_pkg_coll))
    elif license == "Custom":
        # Custom license set in user metadata, no License.txt should exist in package.
        license_file = vault_pkg_coll + "/License.txt"
        if data_object.exists(ctx, license_file):
            data_object.remove(ctx, license_file)
    else:
        # License set in user metadata, a License.txt should exist in package.
        # Check if license text exists.
        license_txt = "/{}{}/{}.txt".format(zone, constants.IILICENSECOLLECTION, license)
        if data_object.exists(ctx, license_txt):
            # Copy license file.
            license_file = vault_pkg_coll + "/License.txt"
            data_object.copy(ctx, license_txt, license_file)

            # Fix ACLs.
            try:
                ctx.iiCopyACLsFromParent(license_file, 'default')
            except Exception as e:
                log.write(ctx, "rule_vault_write_license: Failed to set vault permissions on <{}>".format(license_file))
        else:
            log.write(ctx, "rule_vault_write_license: License text not available for <{}>".format(license))

        # Check if license URI exists.
        license_uri_file = "/{}{}/{}.uri".format(zone, constants.IILICENSECOLLECTION, license)
        if data_object.exists(ctx, license_uri_file):
            # Retrieve license URI.
            license_uri = data_object.read(ctx, license_uri_file)
            license_uri = license_uri.strip()
            license_uri = license_uri.strip('\"')

            # Set license URI.
            avu.set_on_coll(ctx, vault_pkg_coll, "{}{}".format(constants.UUORGMETADATAPREFIX, "license_uri"), license_uri)
        else:
            log.write(ctx, "rule_vault_write_license: License URI not available for <{}>".format(license))


@api.make()
def api_vault_system_metadata(callback, coll):
    """Return collection statistics as JSON."""
    import math

    def convert_size(size_bytes):
        if size_bytes == 0:
            return "0 B"

        size_name = ('B', 'kiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return '{} {}'.format(s, size_name[i])

    system_metadata = {}

    # Package size.
    data_count = collection.data_count(callback, coll)
    collection_count = collection.collection_count(callback, coll)
    size = collection.size(callback, coll)
    size_readable = convert_size(size)
    system_metadata["Package size"] = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    # Modified date.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_lastModifiedDateTime'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        modified_date = row[0]
        system_metadata["Modified date"] = "{}".format(modified_date)

    # Landingpage URL.
    landinpage_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_landingPageUrl'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        landinpage_url = row[0]
        system_metadata["Landingpage"] = "<a href=\"{}\">{}</a>".format(landinpage_url, landinpage_url)

    # Persistent Identifier DOI.
    package_doi = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_yodaDOI'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        package_doi = row[0]
        persistent_identifier_doi = "<a href=\"https://doi.org/{}\">{}</a>".format(package_doi, package_doi)
        system_metadata["Persistent Identifier DOI"] = persistent_identifier_doi

    # Persistent Identifier EPIC.
    package_epic_pid = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_pid'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        package_epic_pid = row[0]

    package_epic_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_url'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:
        package_epic_url = row[0]

    if package_epic_pid:
        if package_epic_url:
            persistent_identifier_epic = "<a href=\"{}\">{}</a>".format(package_epic_url, package_epic_pid)
        else:
            persistent_identifier_epic = "{}".format(package_epic_pid)
        system_metadata["EPIC Persistent Identifier"] = persistent_identifier_epic

    return system_metadata


def get_coll_vault_status(ctx, path, org_metadata=None):
    """Get the status of a vault folder."""
    if org_metadata is None:
        org_metadata = folder.get_org_metadata(ctx, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if constants.IIVAULTSTATUSATTRNAME in org_metadata:
        x = org_metadata[constants.IIVAULTSTATUSATTRNAME]
        try:
            return constants.vault_package_state(x)
        except Exception as e:
            log.write(ctx, 'Invalid vault folder status <{}>'.format(x))

    return constants.vault_package_state.EMPTY


@api.make()
def api_vault_collection_details(ctx, path):
    """Return details of a vault collection."""
    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is a research group.
    space, _, group, _ = pathutil.info(path)
    if space != pathutil.Space.VAULT:
        return {}

    dirname = pathutil.dirname(path)
    basename = pathutil.basename(path)

    # Check if collection is vault package.
    metadata_path = meta.get_latest_vault_metadata_path(ctx, path)
    if metadata_path is None:
        return {}
    else:
        metadata = True

    # Retrieve vault folder status.
    status = get_coll_vault_status(ctx, path).value

    # Check if collection has datamanager.
    has_datamanager = True

    # Check if user is datamanager.
    category = meta_form.group_category(ctx, group)
    is_datamanager = meta_form.user_is_datamanager(ctx, category, user.full_name(ctx))

    # Check if a vault action is pending.
    vault_action_pending = False
    coll_id = collection.id_from_name(ctx, path)

    action_status = constants.UUORGMETADATAPREFIX + '"vault_status_action_' + coll_id
    iter = genquery.row_iterator(
        "COLL_ID",
        "META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + '"vault_status_action_' + coll_id + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
        genquery.AS_LIST, ctx
    )
    for _row in iter:
        vault_action_pending = True

    # Check if research group has access.
    research_group_access = False

    # Retrieve all access user IDs on collection.
    iter = genquery.row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '{}'".format(path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        user_id = row[0]

        # Retrieve all group names with this ID.
        iter2 = genquery.row_iterator(
            "USER_NAME",
            "USER_ID = '{}'".format(user_id),
            genquery.AS_LIST, ctx
        )

        for row2 in iter2:
            user_name = row2[0]

            # Check if group is a research or intake group.
            if user_name.startswith("research-"):
                research_group_access = True

    # Check if research space is accessible.
    research_path = ""
    research_name = group.replace("vault-", "research-", 1)
    if collection.exists(ctx, pathutil.chop(dirname)[0] + "/" + research_name):
        research_path = research_name

    return {"basename": basename,
            "status": status,
            "metadata": metadata,
            "has_datamanager": has_datamanager,
            "is_datamanager": is_datamanager,
            "vault_action_pending": vault_action_pending,
            "research_group_access": research_group_access,
            "research_path": research_path}


@api.make()
def api_vault_get_publication_terms(ctx):
    """Retrieve the publication terms."""
    zone = user.zone(ctx)
    terms_collection = "/{}{}".format(zone, constants.IITERMSCOLLECTION)
    terms = ""

    iter = genquery.row_iterator(
        "DATA_NAME, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '{}'".format(terms_collection),
        genquery.AS_LIST, ctx)

    for row in iter:
        terms = row[0]

    if terms == "":
        return api.Error('TermsNotFound', 'No Terms and Agreements found.')

    try:
        terms_file = "/{}{}/{}".format(zone, constants.IITERMSCOLLECTION, terms)
        return data_object.read(ctx, terms_file)
    except Exception:
        return api.Error('TermsReadFailed', 'Could not open Terms and Agreements.')


def copy_folder_to_vault(ctx, folder, target):
    """Copy folder and all its contents to target in vault.

    The data will reside onder folder '/original' within the vault.

    :param ctx:    Combined type of a callback and rei struct
    :param folder: Path of a folder in the research space
    :param target: Path of a package in the vault space

    :raises Exception: Raises exception when treewalk_and_ingest did not finish correctly
    """
    destination = target + '/original'
    origin = folder

    # Origin is a never changing value to be able to designate a relative path within ingest_object
    error = 0  # Initial error state. Should stay 0.
    if treewalk_and_ingest(ctx, folder, destination, origin, error):
        raise Exception('copy_folder_to_vault: Error copying folder to vault')


def treewalk_and_ingest(ctx, folder, target, origin, error):
    """Treewalk folder and ingest.

    :param ctx:    Combined type of a callback and rei struct
    :param folder: Will change every time as it represents every folder that has to be copied to vault
    :param target: Target of ingest
    :param origin: Origin of treewalk
    :param error:  0/1 indicating if treewalk or ingest failed

    :returns: Error status (which should remain 0 for further processing in iterative manner)
    """
    parent_coll, coll = pathutil.chop(folder)

    # 1. Process this collection itself as a collection.
    # INGEST
    if error == 0:
        # INGEST COLLECTION
        error = ingest_object(ctx, parent_coll, coll, True, target, origin)

    # 2. Process dataobjects located directly within the collection
    if error == 0:
        iter = genquery.row_iterator(
            "DATA_NAME",
            "COLL_NAME = '" + folder + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            # INGEST OBJECT
            error = ingest_object(ctx, folder, row[0], False, target, origin)
            if error:
                break

    if error == 0:
        # 3. Process the subfolders
        # Loop through subfolders which have folder as parent folder
        iter = genquery.row_iterator(
            "COLL_NAME",
            "COLL_PARENT_NAME = '" + folder + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            error = treewalk_and_ingest(ctx, row[0], target, origin, error)
            if error:
                break

    return error


def ingest_object(ctx, parent, item, item_is_collection, destination, origin):
    source_path = parent + "/" + item
    read_access = msi.check_access(ctx, source_path, 'read object', irods_types.BytesBuf())['arguments'][2]

    if read_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:read", user.full_name(ctx), source_path)
        except msi.Error as e:
            return 1

    dest_path = destination

    if source_path != origin:
        markIncomplete = False
        # rewrite path to copy objects that are located underneath the toplevel collection
        source_length = len(source_path)
        relative_path = source_path[len(origin) + 1: source_length]
        dest_path = destination + '/' + relative_path
    else:
        markIncomplete = True

    if item_is_collection:
        # CREATE COLLECTION
        try:
            msi.coll_create(ctx, dest_path, '', irods_types.BytesBuf())
        except msi.Error as e:
            return 1

        if markIncomplete:
            avu.set_on_coll(ctx, dest_path, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.INCOMPLETE)
    else:
        # CREATE COPY OF DATA OBJECT
        try:
            # msi.data_obj_copy(ctx, source_path, dest_path, '', irods_types.BytesBuf())
            ctx.msiDataObjCopy(source_path, dest_path, 'verifyChksum=', 0)
        except msi.Error as e:
            return 1

    if read_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), source_path)
        except msi.Error as e:
            return 1

    return 0


def set_vault_permissions(ctx, group_name, folder, target):
    """Set permissions in the vault as such that data can be copied to the vault."""
    parts = group_name.split('-')
    base_name = '-'.join(parts[1:])

    parts = folder.split('/')
    datapackage_name = parts[-1]
    vault_group_name = constants.IIVAULTPREFIX + base_name

    # Check if noinherit is set
    zone = user.zone(ctx)
    vault_path = "/" + zone + "/home/" + vault_group_name

    inherit = "0"
    iter = genquery.row_iterator(
        "COLL_INHERITANCE",
        "COLL_NAME = '" + vault_path + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # COLL_INHERITANCE can be empty which is interpreted as noinherit
        inherit = row[0]

    if inherit == "1":
        msi.set_acl(ctx, "recursive", "admin:noinherit", "", vault_path)

        # Check if research group has read-only access
        iter = genquery.row_iterator(
            "USER_ID",
            "USER_NAME = '" + group_name + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            group_id = row[0]

        access_name = "null"
        iter = genquery.row_iterator(
            "COLL_ACCESS_NAME",
            "COLL_ACCESS_USER_ID = '" + group_id + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            access_name = row[0]

        if access_name != "read object":
            # Grant the research group read-only access to the collection to enable browsing through the vault.
            try:
                msi.set_acl(ctx, "default", "admin:read", group_name, vault_path)
                log.write(ctx, "Granted " + group_name + " read access to " + vault_path)
            except msi.Error as e:
                log.write(ctx, "Failed to grant " + group_name + " read access to " + vault_path)

    # Check if vault group has ownership
    iter = genquery.row_iterator(
        "USER_ID",
        "USER_NAME = '" + vault_group_name + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        vault_group_id = row[0]

    vault_group_access_name = "null"
    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME",
        "COLL_ACCESS_USER_ID = '" + vault_group_id + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        vault_group_access_name = row[0]

    # Ensure vault-groupName has ownership on vault package
    if vault_group_access_name != "own":
        msi.set_acl(ctx, "recursive", "admin:own", vault_group_name, target)

    # Grant datamanager group read access to vault package.
    category = group.get_category(ctx, group_name)
    datamanager_group_name = "datamanager-" + category

    if group.exists(ctx, datamanager_group_name):
        msi.set_acl(ctx, "recursive", "admin:read", datamanager_group_name, target)

    # Grant research group read access to vault package.
    msi.set_acl(ctx, "recursive", "admin:read", group_name, target)


@rule.make(inputs=range(3), outputs=range(3, 5))
def rule_vault_process_status_transitions(ctx, coll, new_coll_status, actor):
    """Rule interface for processing vault status transition request.

    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Vault collection to change status for
    :param new_coll_status: New vault package status
    :param actor:           Actor of the status change

    :return: Dict with status and statusinfo.
    """
    vault_process_status_transitions(ctx, coll, new_coll_status, actor)

    return 'Success'


def vault_process_status_transitions(ctx, coll, new_coll_status, actor):
    """Processing vault status transition request.

    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Vault collection to change status for
    :param new_coll_status: New vault package status
    :param actor:           Actor of the status change

    :return: Dict with status and statusinfo
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return ['1', 'Insufficient permissions - should only be called by rodsadmin']

    # check current status, perhaps transitioned already
    current_coll_status = get_coll_vault_status(ctx, coll).value
    if current_coll_status == new_coll_status:
        return ['Success', '']

    # Set new status
    try:
        avu.set_on_coll(ctx, coll, constants.IIVAULTSTATUSATTRNAME, new_coll_status)
        if new_coll_status == str(constants.vault_package_state.SUBMITTED_FOR_PUBLICATION):
            send_datamanagers_publication_request_mail(ctx, coll)
        return ['Success', '']
    except msi.Error as e:
        current_coll_status = get_coll_vault_status(ctx, coll).value
        is_legal = policies_datapackage_status.can_transition_datapackage_status(ctx, actor, coll, current_coll_status, new_coll_status)
        if not is_legal:
            return ['1', 'Illegal status transition']
        else:
            if new_coll_status == str(constants.vault_package_state.PUBLISHED):
                # Special case is transition to PUBLISHED
                # landing page and doi have to be present

                # Landingpage URL.
                landinpage_url = ""
                iter = genquery.row_iterator(
                    "META_COLL_ATTR_VALUE",
                    "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_landingPageUrl'" % (coll),
                    genquery.AS_LIST, callback
                )

                for row in iter:
                    if row[0] == "":
                        return ['1', 'Landing page is missing']

                # Persistent Identifier DOI.
                iter = genquery.row_iterator(
                    "META_COLL_ATTR_VALUE",
                    "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_yodaDOI'" % (coll),
                    genquery.AS_LIST, callback
                )

                for row in iter:
                    if row[0] == "":
                        return ['1', 'DOI is missing']

    return ['Success', '']


def send_datamanagers_publication_request_mail(ctx, coll):
    """All involved datamanagers will receive an email notification regarding a publication request by a researcher.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault package with publication request
    """
    # Find group
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]
    group_parts = vault_group_name.split('-')

    # Create the research equivalent in order to get the category.
    group_name = 'research-' + '-'.join(group_parts[1:])

    # Find category.
    category = group.get_category(ctx, group_name)

    # Get the submitter.
    submitter = 'Unknown'
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_submission_actor'" % (coll),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        submitter = row[0].split('#')[0]

    # Find the datamanagers of the category and inform them of data to be accepted to vault
    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_GROUP_NAME = 'datamanager-" + category + "' "
        "AND USER_ZONE = '" + user.zone(ctx) + "' "
        "AND USER_TYPE != 'rodsgroup'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        datamanager = row[0]
        # coll split off zone / home
        mail.mail_datamanager_publication_to_be_accepted(ctx, datamanager, submitter, '/'.join(coll_parts[3:]))


def vault_request_status_transitions(ctx, coll, new_vault_status):
    """Request vault status transition action.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Vault package to be changed of status in publication cycle
    :param new_vault_status: New vault status

    :return: Dict with status and statusinfo
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        if new_vault_status == constants.vault_package_state.PUBLISHED:
            log.write(ctx, "Publication request - User is no rodsadmin")
            return ['PermissionDenied', 'Insufficient permissions - Vault status transition to published can only be requested by a rodsadmin.']
        elif new_vault_status == constants.vault_package_state.DEPUBLISHED:
            log.write(ctx, "depublication request - User is no rodsadmin")
            return ['PermissionDenied', 'Insufficient permissions - Vault status transition to published can only be requested by a rodsadmin.']

    # Determine vault group and actor
    # Find group
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]

    group_parts = vault_group_name.split('-')
    # create the research equivalent in order to get the category
    group_name = 'research-' + '-'.join(group_parts[1:])

    # Find category
    category = group.get_category(ctx, group_name)
    zone = user.zone(ctx)
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]

    # User/actor specific stuff
    actor = user.full_name(ctx)

    actor_group = folder.collection_group_name(ctx, coll)
    if actor_group == '':
        log.write(ctx, "Cannot determine which research group " + coll + " belongs to")
        return ['1', '']

    is_datamanager = meta_form.user_member_type(ctx, 'datamanager-' + category, actor) in ['normal', 'manager']

    actor_group_path = '/' + zone + '/home/'

    # Status SUBMITTED_FOR_PUBLICATION can only be requested by researcher.
    # Status UNPUBLISHED can be called by researcher and datamanager.
    # HIER NOG FF NAAR KIJKEN
    if not is_datamanager:
        if new_vault_status in [constants.vault_package_state.SUBMITTED_FOR_PUBLICATION, constants.vault_package_state.UNPUBLISHED]:
            actor_group_path = '/' + zone + '/home/' + actor_group
    else:
        actor_group_path = '/' + zone + '/home/datamanager-' + category

#        if (*newVaultStatus == SUBMITTED_FOR_PUBLICATION && !*isDatamanager) {
#                *actorGroupPath = "/*rodsZone/home/*actorGroup";
#        # Status UNPUBLISHED can be called by researcher and datamanager.
#        } else  if (*newVaultStatus == UNPUBLISHED && !*isDatamanager) {
#                *actorGroupPath = "/*rodsZone/home/*actorGroup";
#        } else  if (*isDatamanager) {
#                iiDatamanagerGroupFromVaultGroup(*vaultGroup, *actorGroup);
#                *actorGroupPath = "/*rodsZone/home/*actorGroup";
#        }

    # Retrieve collection id.
    coll_id = collection.id_from_name(ctx, coll)

    # Check if vault package is currently pending for status transition.
    # Except for status transition to PUBLISHED/DEPUBLISHED,
    # because it is requested by the system before previous pending
    # transition is removed.
    if new_vault_status != constants.vault_package_state.PUBLISHED and new_vault_status != constants.vault_package_state.DEPUBLISHED:
        action_status = constants.UUORGMETADATAPREFIX + '"vault_status_action_' + coll_id
        iter = genquery.row_iterator(
            "COLL_ID",
            "META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + '"vault_status_action_' + coll_id + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
            genquery.AS_LIST, ctx
        )
        for _row in iter:
            # Don't accept request if a status transition is already pending.
            return ['PermissionDenied', "Vault package is being processed, please wait until finished."]

    # Check if status transition is allowed.
    current_vault_status = get_coll_vault_status(ctx, coll).value

    is_legal = policies_datapackage_status.can_transition_datapackage_status(ctx, actor, coll, current_vault_status, new_vault_status)
    if not is_legal:
        return ['PermissionDenied', 'Illegal status transition']

    # Add vault action request to actor group.
    avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'vault_action_' + coll_id, jsonutil.dump([coll, str(new_vault_status), actor]))
    # opposite is: jsonutil.parse('["coll","status","actor"]')[0] => coll

    # Add vault action status to actor group.
    avu.set_on_coll(ctx, actor_group_path, constants.UUORGMETADATAPREFIX + 'vault_status_action_' + coll_id, 'PENDING')

    return ['', '']
