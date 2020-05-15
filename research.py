# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import meta_form
import folder

import time
import os
from pathvalidate import ValidationError, validate_filename, validate_filepath

from util import *

import irods_types

from util.query import Query

__all__ = ['api_uu_research_folder_add',
           'api_uu_research_folder_delete',
           'api_uu_research_folder_rename',
           'api_uu_research_file_rename',
           'api_uu_research_file_delete',
           'api_uu_research_revision_restore',
           'api_uu_research_revisions_search_on_filename',
           'api_uu_research_revision_list',
           'api_uu_research_system_metadata',
           'api_uu_research_collection_details']


@api.make()
def api_uu_research_folder_add(ctx,
                               coll,
                               new_folder_name):

    coll_target = coll + '/' + new_folder_name

    if len(new_folder_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a folder name"}

    try:
        validate_filepath(coll_target)
    except ValidationError as e:
        return {"proc_status": "nok",
                "proc_status_info": "This is not a correct folder name. Please choose another name for your folder"}

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to add folder '" + new_folder_name + "' at this location"}

    # Name should not contain '\\' or '/'
    if '/' in new_folder_name or '\\' in new_folder_name:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in the folder name to be deleted"}

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete folders from the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to delete the selected folder"}

    # coll exists?
    if not collection.exists(ctx, coll):
        return {"proc_status": "nok",
                "proc_status_info": "The selected folder to add a new folder to does not exist"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, coll)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore can not be deleted"}

    # new collection exists?
    if collection.exists(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The folder already exists. Please choose another name"}

    # All requirements OK
    try:
        collection.create(ctx, coll_target)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_uu_research_folder_rename(ctx,
                                  new_folder_name,
                                  coll,
                                  org_folder_name):

    coll_target = coll + '/' + new_folder_name

    if len(new_folder_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a folder name"}

    try:
        validate_filepath(coll_target)
    except ValidationError as e:
        return {"proc_status": "nok",
                "proc_status_info": "This is not a correct folder name. Please choose another name for your folder"}

    # Same name makes no sense
    if new_folder_name == org_folder_name:
        return {"proc_status": "nok",
                "proc_status_info": "Origin and target folder names are equal. Please choose another name"}

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to add folder '" + folder_name + "' at this location"}

    # Name should not contain '\\' or '/'
    if '/' in new_folder_name or '\\' in new_folder_name:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in the folder name to be deleted"}

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete folders from the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to delete the selected folder"}

    # coll exists?
    if not collection.exists(ctx, coll):
        return {"proc_status": "nok",
                "proc_status_info": "The selected folder to add a new folder to does not exist"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, coll)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore can not be deleted"}

    # new collection exists?
    if collection.exists(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The folder already exists. Please choose another name"}

    # All requirements OK
    try:
        collection.rename(ctx, coll + '/' + org_folder_name, coll_target)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_uu_research_folder_delete(ctx,
                                  coll,
                                  folder_name):
    coll_target = coll + '/' + folder_name

    # Not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete folder '" + folder_name + "' at this location"}

    # Name should not contain '\\' or '/'.
    if '/' in folder_name or '\\' in folder_name:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in the folder name to be deleted"}

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete folders from the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to delete the selected folder"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, coll_target)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore can not be deleted"}

    # collection exists?
    if not collection.exists(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The selected folder to add a new folder to does not exist"}

    # Folder empty?
    if not collection.empty(ctx, coll_target) or collection.collection_count(ctx, coll_target) > 0:
        return {"proc_status": "nok",
                "proc_status_info": "The selected folder is not empty and can therefore not be deleted. Please delete entire content first"}

    # All requirements OK
    try:
        collection.remove(ctx, coll_target)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_uu_research_file_rename(ctx,
                                new_file_name,
                                coll,
                                org_file_name):

    if len(new_file_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a file name"}

    try:
        validate_filename(new_file_name)
    except Exception:
        return {"proc_status": "nok",
                "proc_status_info": "This is not a valid file name. Please choose another name"}

    # Same name makes no sense
    if new_file_name == org_file_name:
        return {"proc_status": "nok",
                "proc_status_info": "Origin and target file names are equal. Please choose another name"}

    path_target = coll + '/' + new_file_name

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible rename files at this location"}

    # Name should not contain '\\' or '/'
    if '/' in new_file_name or '\\' in new_file_name:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in the new name of a file"}

    # in vault?
    target_group_name = path_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to rename files in the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to rename the selected file"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, coll)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore the indicated file can not be renamed"}

    # DOes org file exist?
    if not data_object.exists(ctx, coll + '/' + org_file_name):
        return {"proc_status": "nok",
                "proc_status_info": "The original file " + org_file_name + " can not be found"}

    # new filename already exists?
    if data_object.exists(ctx, path_target):
        return {"proc_status": "nok",
                "proc_status_info": "The selected filename " + new_file_name + " already exists"}

    # All requirements OK
    try:
        data_object.rename(ctx, coll + '/' + org_file_name, path_target)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_uu_research_file_delete(ctx,
                                coll,
                                file_name):

    path_target = coll + '/' + file_name

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete files at this location"}

    # in vault?
    target_group_name = path_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to delete files from the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to delete the selected file"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, path_target)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore the indicated file can not be deleted"}

    # collection exists?
    if not data_object.exists(ctx, path_target):
        return {"proc_status": "nok",
                "proc_status_info": "The selected folder to add a new folder to does not exist"}

    # All requirements OK
    try:
        data_object.remove(ctx, path_target)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_uu_research_revisions_search_on_filename(ctx,
                                                 searchString,
                                                 offset=0,
                                                 limit=10):

    zone = user.zone(ctx)

    revisions = []

    # Return nothing if in fact requested ALL
    if len(searchString) == 0:
        return {'total': 0,
                'items': revisions}

    originalDataNameKey = constants.UUORGMETADATAPREFIX + 'original_data_name'
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    qdata = Query(ctx, ['COLL_NAME', 'META_DATA_ATTR_VALUE'],
                  "META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
                  "AND META_DATA_ATTR_VALUE like '" + searchString + "%' "
                  "AND COLL_NAME like '" + startpath + "%' ",
                  offset=offset, limit=limit, output=query.AS_DICT)

    # step through results and enrich with wanted data
    for rev in list(qdata):
        rev_data = {}
        rev_data['main_revision_coll'] = rev['COLL_NAME']
        rev_data['main_original_dataname'] = rev['META_DATA_ATTR_VALUE']

        iter = genquery.row_iterator(
            "DATA_ID",
            "COLL_NAME = '" + rev_data['main_revision_coll'] + "' "
            "AND META_DATA_ATTR_NAME = '" + originalDataNameKey + "' "
            "AND META_DATA_ATTR_VALUE = '" + rev_data['main_original_dataname'] + "' ",  # *originalDataName
            genquery.AS_DICT, ctx)

        revision_count = 0
        for row in iter:
            revision_count = revision_count + 1

            # based on data id get original_coll_name
            iter2 = genquery.row_iterator(
                "META_DATA_ATTR_VALUE",
                "DATA_ID = '" + row['DATA_ID'] + "' "
                "AND META_DATA_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'original_path' + "' ",
                genquery.AS_DICT, ctx)
            for row2 in iter2:
                rev_data['original_coll_name'] = row2['META_DATA_ATTR_VALUE']

            rev_data['collection_exists'] = collection.exists(ctx, '/'.join(rev_data['original_coll_name'].split(os.path.sep)[:-1]))
            rev_data['original_coll_name'] = '/'.join(rev_data['original_coll_name'].split(os.path.sep)[3:])

        rev_data['revision_count'] = revision_count

        revisions.append(rev_data)

    return {'total': len(list(qdata)),
            'items': revisions}


@api.make()
def api_uu_research_revision_list(ctx, path):

    originalPathKey = ''
    startpath = ''

    zone = user.zone(ctx)

    revisions = []
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    startpath = '/' + zone + constants.UUREVISIONCOLLECTION

    iter = genquery.row_iterator(
        "DATA_ID, COLL_NAME, order(DATA_NAME)",
        "META_DATA_ATTR_NAME = '" + originalPathKey + "' "
        "AND META_DATA_ATTR_VALUE = '" + path + "' "
        "AND COLL_NAME like '" + startpath + "%' ",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        revisionPath = row[1] + '/' + row[2]

        iter2 = genquery.row_iterator(
            "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE ",
            "DATA_ID = '" + row[0] + "' ",
            genquery.AS_LIST, ctx
        )

        meta_data = {"data_id": row[0]}
        for row2 in iter2:
            meta_data[row2[0]] = row2[1]

        meta_data["dezoned_coll_name"] = '/' + '/'.join(meta_data["org_original_coll_name"].split(os.path.sep)[3:])

        meta_data["org_original_modify_time"] = time.strftime('%Y/%m/%d %H:%M:%S',
                                                              time.localtime(int(meta_data["org_original_modify_time"])))

        revisions.append(meta_data)

    return {"revisions": revisions}


@api.make()
# "restore_no_overwrite"
# "restore_overwrite" -> overwrite the file
# "restore_next_to" -> revision is places next to the file it conficted with by adding
#
# {restore_no_overwrite, restore_overwrite, restore_next_to}
#   With "restore_no_overwrite" the front end tries to copy the selected revision in *target
#    If the file already exist the user needs to decide what to do.
#     Function exits with corresponding status so front end can take action
def api_uu_research_revision_restore(ctx, revision_id, overwrite, coll_target, new_filename):
    """Copy selected revision to target collection with given name"""
    # New file name should not contain '\\' or '/'
    if '/' in new_filename or '\\' in new_filename:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in a filename"}

    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to store file in the vault"}

    # Check existance of target_coll
    if not collection.exists(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The target collection does not exist or is not accessible for you"}

    user_full_name = user.full_name(ctx)

    # Target collection write access ?
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You are not allowed to write in the selected collection"}

    # Target_coll locked?
    if folder.is_locked(ctx, coll_target):
        return {"proc_status": "nok",
                "proc_status_info": "The target collection is locked and therefore this revision cannot be written to the indicated collection"}

    # Read acces in org collection??
    # Find actual revision inf on revision_id
    originalPathKey = constants.UUORGMETADATAPREFIX + 'original_path'
    original_path   = ''
    source_path     = ''
    coll_origin     = ''
    filename_origin = ''
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME, META_DATA_ATTR_VALUE",
        "DATA_ID = '" + revision_id + "' "
        " AND META_DATA_ATTR_NAME = '" + originalPathKey + "' ",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        coll_origin = row[1]
        filename_origin = row[0]
        original_path = row[2]

    origin_group_name = original_path.split('/')[3]

    if meta_form.user_member_type(ctx, origin_group_name, user_full_name) in ['none']:
        return {"proc_status": "nok",
                "proc_status_info": "You are not allowed to view the information from this group " + origin_group_name}

    source_path = coll_origin + "/"  + filename_origin

    if source_path == '':
        return {"proc_status": "nok",
                "proc_status_info": "The indicated revision does not exist"}

    if overwrite in ["restore_no_overwrite", "restore_next_to"]:
        if data_object.exists(ctx, coll_target + '/' + new_filename):
            return {"proc_status": "ok_duplicate",
                    "proc_status_info": "The file is already present at the indicated location"}

    elif overwrite in ["restore_overwrite"]:
        restore_allowed = True

    else:
        return {"proc_status": "nok",
                "proc_status_info": "Unkown requested action: " + overwrite}

    # Allowed to restore revision
    # Start actual restoration of the revision
    try:
        # Workaround the PREP deadlock issue: Restrict threads to 1.
        ofFlags = 'forceFlag=++++numThreads=1'
        msi.data_obj_copy(ctx, source_path, coll_target + '/' + new_filename, ofFlags, irods_types.BytesBuf())
    except msi.Error as e:
        raise api.Error('copy_failed', 'The file could not be copied', str(e))

    return {"proc_status": "ok"}


@api.make()
def api_uu_research_system_metadata(ctx, coll):
    """Returns collection statistics as JSON."""

    import math

    def convert_size(size_bytes):
        if size_bytes == 0:
            return "0 B"

        size_name = ('B', 'kiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return '{} {}'.format(s, size_name[i])

    data_count = collection.data_count(ctx, coll)
    collection_count = collection.collection_count(ctx, coll)
    size = collection.size(ctx, coll)
    size_readable = convert_size(size)

    result = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    return {"Package size": result}


@api.make()
def api_uu_research_collection_details(ctx, path):
    """Returns details of a research collection."""

    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is a research group.
    space, _, group, _ = pathutil.info(path)
    if space != pathutil.Space.RESEARCH:
        return {}

    basename = pathutil.chop(path)[1]

    # Retrieve user type.
    member_type = meta_form.user_member_type(ctx, group, user.full_name(ctx))

    # Retrieve research folder status.
    status = folder.get_status(ctx, path)

    # Check if user is datamanager.
    category = meta_form.group_category(ctx, group)
    is_datamanager = meta_form.user_is_datamanager(ctx, category, user.full_name(ctx))

    # Retrieve lock count.
    lock_count = meta_form.get_coll_lock_count(ctx, path)

    # Check if vault is accessible.
    vault_path = ""
    vault_name = group.replace("research-", "vault-", 1)
    if collection.exists(ctx, pathutil.chop(path)[0] + "/" + vault_name):
        vault_path = vault_name

    return {"basename": basename,
            "status": status.value,
            "member_type": member_type,
            "is_datamanager": is_datamanager,
            "lock_count": lock_count,
            "vault_path": vault_path}
