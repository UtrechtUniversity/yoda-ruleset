# -*- coding: utf-8 -*-
"""Functions for intake vault."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime
import time

import intake_lock
import intake_scan
from util import *

__all__ = ['rule_intake_to_vault']


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
            status = dataset_collection_move_2_vault(ctx, toplevel_collection, dataset_id, vault_root)
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
            status = dataset_objects_only_move_2_vault(ctx, toplevel_collection, dataset_id, vault_root)
            if status == 0:
                datasets_moved += 1

    if datasets_moved:
        log.write(ctx, "Datasets moved to the vault: " + str(datasets_moved))

    return 0


def dataset_collection_move_2_vault(ctx, toplevel_collection, dataset_id, vault_root):
    """Move intake datasets consisting of collections to the vault

    :param ctx:                 Combined type of a callback and rei struct
    :param toplevel_collection: Toplevel collection
    :param dataset_id:          Identifier of dataset
    :param vault_root:          Root path of vault

    :returns: Status
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
        # stamp the vault dataset collection with additional metadata
        # date_created = datetime.now()
        # avu.set_on_coll(ctx, vault_path, "dataset_date_created", date_created.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))

        avu.set_on_coll(ctx, vault_path, "dataset_date_created", str(int(time.time())))

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


def dataset_objects_only_move_2_vault(ctx, toplevel_collection, dataset_id, vault_root):
    """Move intake datasets consisting of data objects to the vault

    :param ctx:                 Combined type of a callback and rei struct
    :param toplevel_collection: Toplevel collection
    :param dataset_id:          Identifier of dataset
    :param vault_root:          Root path of vault

    :returns: Status
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
        collection.create(ctx, vault_path, "1")
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
        "COLL_NAME = '" + toplevel_collection + "' "
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
            "COLL_NAME = '" + toplevel_collection + "' "
            "AND META_DATA_ATTR_NAME = 'dataset_toplevel' "
            "AND META_DATA_ATTR_VALUE = '" + dataset_id + "' ",
            genquery.AS_LIST, ctx)

        for row in iter:
            intake_path = toplevel_collection + "/" + row[0]
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
    """Walk a subtree and perfom 'rule_to_process' per item.

    :param ctx:             Combined type of a callback and rei struct
    :param path:            Path of collection to treewalk
    :param buffer:          Exclusively to be used by the rule we will can
    :param rule_to_process: Name of the rule to be executed in the context of a tree-item

    :returns: Error status
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
    # my_date = datetime.now()
    # id_components["dataset_date_created"] = my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    id_components["dataset_date_created"] = str(int(time.time()))


    keys = ["wave", "experiment_type", "pseudocode", "version", "dataset_date_created"]
    for key in keys:
        try:
            avu.set_on_data(ctx, vault_path, key, id_components[key])
        except Exception as e:
            avu.set_on_coll(ctx, vault_path, key, id_components[key])


def vault_dataset_exists(ctx, vault_root, dataset_id):
    id_components = intake_scan.dataset_parse_id(dataset_id)
    # Beware! extra 'ver' before version from orginal code: *wepv = *wave ++ *sep ++ *experimentType ++ *sep ++ *pseudocode ++ *sep ++ "ver*version";
    wepv = id_components["wave"] + "_" + id_components["experiment_type"] + "_" + id_components["pseudocode"] + "_ver" + id_components["version"]
    dataset_path = vault_root + '/' + id_components["wave"] + "/" + id_components["experiment_type"] + "/" + id_components["pseudocode"] + "/" + wepv

    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME = '" + dataset_path + "' ",
        genquery.AS_LIST, ctx)

    for _row in iter:
        return True

    return False


def get_dataset_path(root, dataset_id):
    id_components = intake_scan.dataset_parse_id(dataset_id)
    # Beware! extra 'ver' before version from orginal code: *wepv = *wave ++ *sep ++ *experimentType ++ *sep ++ *pseudocode ++ *sep ++ "ver*version";
    wepv = id_components["wave"] + "_" + id_components["experiment_type"] + "_" + id_components["pseudocode"] + "_ver" + id_components["version"]

    return root + '/' + id_components["wave"] + "/" + id_components["experiment_type"] + "/" + id_components["pseudocode"] + "/" + wepv
