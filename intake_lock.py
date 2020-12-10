
import time

import genquery
from rules_uu.util import *


def intake_dataset_treewalk_change_status(ctx, collection, status, timestamp, remove):
    """Treewalk dataset collection and change status.

    :param ctx:        Combined type of a callback and rei struct
    :param collection: Will change every time as it represents every collection that has to be processed
    :param status:     Status to set on dataset objects
    :param timestamp:  Timestamp of status change
    :param remove:     Boolean, set or remove status
    """

    log.write(ctx, collection)
    log.write(ctx, status)

    # 1. Change status on this collection.
    if remove:
        avu.rmw_from_coll(ctx, collection, status, "%")
    else:
        log.write(ctx, 'step1 . set_on_col')
        avu.set_on_coll(ctx, collection, status, timestamp)

    # 2. Change status on data objects located directly within the collection.
    data_objects = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME = '{}'".format(collection),
        genquery.AS_LIST, ctx
    )

    for row in data_objects:
        if remove:
            avu.rmw_from_data(ctx, "{}/{}".format(collection, row[0]), status, "%")
        else:
            log.write(ctx, 'step2 . set_on_data')
            avu.set_on_data(ctx, "{}/{}".format(collection, row[0]), status, timestamp)

    # 3. Loop through subcollections.
    subcollections = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '{}'".format(collection),
        genquery.AS_LIST, ctx
    )

    for row in subcollections:
        intake_dataset_treewalk_change_status(ctx, row[0], status, timestamp, remove)


def intake_dataset_change_status(ctx, object, is_collection, dataset_id, status, timestamp, remove):
    """Change status on dataset.

    :param ctx:           Combined type of a callback and rei struct
    :param object:        Will change every time as it represents every object of the dataset
    :param is_collection: Indicator if dataset is within a collection
    :param dataset_id:    Dataset identifier
    :param status:        Status to set on dataset objects
    :param timestamp:     Timestamp of status change
    :param remove:        Boolean, set or remove status
    """
    # Is dataset a collection?
    if is_collection:
        # Recursively change the status on all objects in the dataset
        intake_dataset_treewalk_change_status(ctx, object, status, timestamp, remove)
    else:
        # Dataset is not a collection, find all the dataset objects.
        data_objects = genquery.row_iterator("DATA_NAME",
                                             "COLL_NAME = '{}' AND META_DATA_ATTR_NAME = 'dataset_toplevel' AND META_DATA_ATTR_VALUE = '{}'".format(object, dataset_id),
                                             genquery.AS_LIST, ctx)

        # Change dataset status on all objects.
        for row in data_objects:
            if remove:
                avu.rmw_from_data(ctx, "{}/{}".format(object, row[0]), status, "%")
            else:
                avu.set_on_data(ctx, "{}/{}".format(object, row[0]), status, timestamp)


def intake_dataset_lock(ctx, collection, dataset_id):
    timestamp = str(int(time.time()))

    log.write(ctx, collection)

    tl_info = get_dataset_toplevel_objects(ctx, collection, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']
    log.write(ctx, tl_info)

    if is_collection:
        intake_dataset_change_status(ctx, tl_objects[0], is_collection, dataset_id, "to_vault_lock", timestamp, False)
    else:
        # Dataset based on 
        for tl_object in tl_objects:
            avu.set_on_data(ctx, tl_object, "to_vault_lock", timestamp)


def intake_dataset_unlock(ctx, collection, dataset_id):
    timestamp = str(int(time.time()))

    log.write(ctx, collection)

    tl_info = get_dataset_toplevel_objects(ctx, collection, dataset_id)
    is_collection = tl_info['is_collection']
    tl_objects = tl_info['objects']
    log.write(ctx, tl_info)

    if is_collection:
        intake_dataset_change_status(ctx, tl_objects[0], is_collection, dataset_id, "to_vault_lock", timestamp, True)
    else:
        # Dataset based on
        for tl_object in tl_objects:
            avu.rmw_from_data(ctx, tl_object, "to_vault_lock", status, "%")


def intake_dataset_freeze(ctx, collection, dataset_id):
    timestamp = str(int(time.time()))
    top_collection = ""
    is_collection = ""
    ctx.uuYcDatasetGetTopLevel(collection, dataset_id, top_collection, is_collection)

    intake_dataset_change_status(ctx, top_collection, is_collection, dataset_id, "to_vault_freeze", timestamp, False)


def intake_dataset_melt(ctx, collection, dataset_id):
    timestamp = str(int(time.time()))
    top_collection = ""
    is_collection = ""
    ctx.uuYcDatasetGetTopLevel(collection, dataset_id, top_collection, is_collection)

    intake_dataset_change_status(ctx, top_collection, is_collection, dataset_id, "to_vault_freeze", timestamp, True)


def intake_dataset_object_get_status(ctx, path):
    """Get the status of an object in a dataset.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of dataset object

    :returns: Tuple booleans indicating if the object is locked or frozen
    """
    locked = False
    frozen = False

    if collecton.exists(ctx, path):
        attribute_names = genquery.row_iterator("META_COLL_ATTR_NAME",
                                                "COLL_NAME = '{}'".format(path),
                                                genquery.AS_LIST, ctx)
    else:
        coll_name, data_name = pathutil.chop(path)
        attribute_names = genquery.row_iterator("META_DATA_ATTR_NAME",
                                                "COLL_NAME = '{}' AND DATA_NAME = '{}'".format(coll_name, data_name),
                                                genquery.AS_LIST, ctx)

    for row in attribute_names:
        attribute_name = row[0]
        if attribute_name in ["to_vault_lock", "to_vault_freeze"]:
            locked = True

            if attribute_name == "to_vault_freeze":
                frozen = True
                break

    return locked, frozen
