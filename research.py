# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pathvalidate import validate_filename, validate_filepath, ValidationError

import folder
import meta_form
from util import *

__all__ = ['api_research_folder_add',
           'api_research_folder_delete',
           'api_research_folder_rename',
           'api_research_file_copy',
           'api_research_file_rename',
           'api_research_file_delete',
           'api_research_system_metadata',
           'api_research_collection_details']


@api.make()
def api_research_folder_add(ctx, coll, new_folder_name):
    """Add a new folder to a research folder.

    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Collection to create new folder in
    :param new_folder_name: Name of the new folder

    :returns: Dict with API status result
    """
    coll_target = coll + '/' + new_folder_name

    if len(new_folder_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a folder name"}

    try:
        validate_filepath(coll_target.decode('utf-8'))
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

    # Name should not be '.' or '..'
    if new_folder_name == '.' or new_folder_name == '..':
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to name the folder {}".format(new_folder_name)}

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
def api_research_folder_rename(ctx, new_folder_name, coll, org_folder_name):
    """Rename an existing research folder.

    :param ctx:             Combined type of a callback and rei struct
    :param new_folder_name: New folder name
    :param coll:            Parent collection of folder
    :param org_folder_name: Current name of the folder

    :returns: Dict with API status result
    """
    coll_target = coll + '/' + new_folder_name

    if len(new_folder_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a folder name"}

    try:
        validate_filepath(coll_target.decode('utf-8'))
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

    # Name should not be '.' or '..'
    if new_folder_name == '.' or new_folder_name == '..':
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to name the folder {}".format(new_folder_name)}

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
def api_research_folder_delete(ctx, coll, folder_name):
    """Delete a research folder.

    :param ctx:         Combined type of a callback and rei struct
    :param coll:        Parent collection of folder to delete
    :param folder_name: Name of folder to delete

    :returns: Dict with API status result
    """
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
def api_research_file_copy(ctx, copy, coll, file):
    """Copy a file in a research folder.

    :param ctx:  Combined type of a callback and rei struct
    :param copy: New file name
    :param coll: Parent collection of file
    :param file: Current name of the file

    :returns: Dict with API status result
    """
    if len(copy) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a file name"}

    try:
        validate_filename(copy.decode('utf-8'))
    except Exception:
        return {"proc_status": "nok",
                "proc_status_info": "This is not a valid file name. Please choose another name"}

    # Same name makes no sense
    if copy == file:
        return {"proc_status": "nok",
                "proc_status_info": "Origin and copy file names are equal. Please choose another name"}

    path_target = coll + '/' + copy

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible copy files at this location"}

    # Name should not contain '\\' or '/'
    if '/' in copy or '\\' in copy:
        return {"proc_status": "nok",
                "proc_status_info": "It is not allowed to use slashes in the new name of a file"}

    # in vault?
    target_group_name = path_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return {"proc_status": "nok",
                "proc_status_info": "It is not possible to copy files in the vault"}

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return {"proc_status": "nok",
                "proc_status_info": "You do not have sufficient permissions to copy the selected file"}

    # folder not locked?
    lock_count = meta_form.get_coll_lock_count(ctx, coll)
    if lock_count:
        return {"proc_status": "nok",
                "proc_status_info": "The indicated folder is locked and therefore the indicated file can not be copied"}

    # DOes org file exist?
    if not data_object.exists(ctx, coll + '/' + file):
        return {"proc_status": "nok",
                "proc_status_info": "The original file " + file + " can not be found"}

    # new filename already exists?
    if data_object.exists(ctx, path_target):
        return {"proc_status": "nok",
                "proc_status_info": "The selected filename " + copy + " already exists"}

    # All requirements OK
    try:
        data_object.copy(ctx, coll + '/' + file, coll + '/' + copy)
    except msi.Error as e:
        return {"proc_status": "nok",
                "proc_status_info": "Something went wrong. Please try again"}

    return {"proc_status": "ok",
            "proc_status_info": ""}


@api.make()
def api_research_file_rename(ctx, new_file_name, coll, org_file_name):
    """Rename a file in a research folder.

    :param ctx:           Combined type of a callback and rei struct
    :param new_file_name: New file name
    :param coll:          Parent collection of file
    :param org_file_name: Current name of the file

    :returns: Dict with API status result
    """
    if len(new_file_name) == 0:
        return {"proc_status": "nok",
                "proc_status_info": "Please add a file name"}

    try:
        validate_filename(new_file_name.decode('utf-8'))
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
def api_research_file_delete(ctx, coll, file_name):
    """Delete a file in a research folder.

    :param ctx:       Combined type of a callback and rei struct
    :param coll:      Parent collection of file to delete
    :param file_name: Name of file to delete

    :returns: Dict with API status result
    """
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
def api_research_system_metadata(ctx, coll):
    """Return collection statistics as JSON.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Research collection

    :returns: Dict with research system metadata
    """
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
def api_research_collection_details(ctx, path):
    """Return details of a research collection."""
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
