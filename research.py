# -*- coding: utf-8 -*-
"""Functions for the research space."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
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
        return api.Error('missing_foldername', 'Missing folder name. Please add a folder name')

    try:
        validate_filepath(coll_target.decode('utf-8'))
    except ValidationError as e:
        return api.Error('invalid_foldername', 'This is not a valid folder name. Please choose another name for your folder')

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return api.Error('invalid_destination', 'It is not possible to add folder ' + new_folder_name + ' at this location')

    # Name should not contain '\\' or '/'
    if '/' in new_folder_name or '\\' in new_folder_name:
        return api.Error('invalid_foldername', 'It is not allowed to use slashes in a folder name')

    # Name should not be '.' or '..'
    if new_folder_name == '.' or new_folder_name == '..':
        return api.Error('invalid_foldername', 'It is not allowed to name the folder {}'.format(new_folder_name))

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('not_allowed', 'It is not possible to add folders in the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to add new folders')

    # Collection exists?
    if not collection.exists(ctx, coll):
        return api.Error('invalid_foldername', 'The selected folder to add a new folder to does not exist')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked so no new folders can be added to it')

    # new collection exists?
    if collection.exists(ctx, coll_target):
        return api.Error('invalid_foldername', 'The folder already exists. Please choose another name')

    # All requirements OK
    try:
        collection.create(ctx, coll_target)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


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
        return api.Error('missing_foldername', 'Missing folder name. Please add a folder name')

    try:
        validate_filepath(coll_target.decode('utf-8'))
    except ValidationError as e:
        return api.Error('invalid_foldername', 'This is not a valid folder name. Please choose another name for your folder')

    # Same name makes no sense
    if new_folder_name == org_folder_name:
        return api.Error('invalid_foldername', 'Origin and target folder names are equal. Please choose another name')

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return api.Error('invalid_destination', 'It is not possible to add folder ' + folder_name + ' at this location')

    # Name should not contain '\\' or '/'
    if '/' in new_folder_name or '\\' in new_folder_name:
        return api.Error('invalid_foldername', 'It is not allowed to use slashes in the new folder name')

    # Name should not be '.' or '..'
    if new_folder_name == '.' or new_folder_name == '..':
        return api.Error('invalid_foldername', 'It is not allowed to name the folder {}'.format(new_folder_name))

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('not_allowed', 'It is not possible to rename folders in the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to rename the selected folder')

    # Collection exists?
    if not collection.exists(ctx, coll):
        return api.Error('invalid_foldername', 'The selected folder does not exist')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore can not be renamed')

    # new collection exists?
    if collection.exists(ctx, coll_target):
        return api.Error('invalid_foldername', 'The folder already exists. Please choose another name')

    # All requirements OK
    try:
        collection.rename(ctx, coll + '/' + org_folder_name, coll_target)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


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
        return api.Error('invalid_target', 'It is not possible to delete folder ' + folder_name + ' at this location')

    # Name should not contain '\\' or '/'.
    if '/' in folder_name or '\\' in folder_name:
        return api.Error('invalid_foldername', 'It is not allowed to use slashes in folder name to be delete')

    # in vault?
    target_group_name = coll_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('not_allowed', 'It is not possible to delete folders from the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to delete the selected folder')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore can not be deleted')

    # Collection exists?
    if not collection.exists(ctx, coll_target):
        return api.Error('invalid_target', 'The folder to delete does not exist')

    # All requirements OK
    try:
        collection.remove(ctx, coll_target)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


@api.make()
def api_research_file_copy(ctx, filepath, new_filepath):
    """Copy a file in a research folder.

    :param ctx:          Combined type of a callback and rei struct
    :param filepath:     Path to the file to copy
    :param new_filepath: Path to the new copy of the file

    :returns: Dict with API status result
    """
    if len(new_filepath) == 0:
        return api.Error('missing_filepath', 'Missing file path. Please add a file path')

    # Same filepath makes no sense.
    if filepath == new_filepath:
        return api.Error('invalid_filepath', 'Origin and copy file paths are equal. Please choose another destination')

    coll = pathutil.chop(new_filepath)[0]
    data_name = pathutil.chop(new_filepath)[1]
    try:
        validate_filename(data_name.decode('utf-8'))
    except Exception:
        return api.Error('invalid_filename', 'This is not a valid file name. Please choose another name')

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return api.Error('invalid_destination', 'It is not possible to copy files at this location')

    # Name should not contain '\\' or '/'
    if '/' in data_name or '\\' in data_name:
        return api.Error('invalid_filename', 'It is not allowed to use slashes in the new name of a file')

    # in vault?
    target_group_name = new_filepath.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('invalid_destination', 'It is not possible to copy files in the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to copy the selected file')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore the indicated file can not be copied')

    # Does org file exist?
    if not data_object.exists(ctx, filepath):
        return api.Error('invalid_source', 'The original file ' + data_name + ' can not be found')

    # new filename already exists?
    if data_object.exists(ctx, new_filepath):
        return api.Error('invalid_destination', 'The file ' + data_name + ' already exists')

    # All requirements OK
    try:
        data_object.copy(ctx, filepath, new_filepath)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


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
        return api.Error('missing_filename', 'Missing filename. Please add a file name')

    try:
        validate_filename(new_file_name.decode('utf-8'))
    except Exception:
        return api.Error('invalid_filename', 'This is not a valid file name. Please choose another name')

    # Same name makes no sense
    if new_file_name == org_file_name:
        return api.Error('invalid_filename', 'Origin and target file names are equal. Please choose another name')

    path_target = coll + '/' + new_file_name

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return api.Error('invalid_destination', 'It is not possible to rename files at this location')

    # Name should not contain '\\' or '/'
    if '/' in new_file_name or '\\' in new_file_name:
        return api.Error('invalid_filename', 'It is not allowed to use slashes in the new name of a file')

    # in vault?
    target_group_name = path_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('invalid_destination', 'It is not possible to rename files in the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to rename the selected file')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore the indicated file can not be renamed')

    # Does org file exist?
    if not data_object.exists(ctx, coll + '/' + org_file_name):
        return api.Error('invalid_source', 'The original file ' + org_file_name + ' can not be found')

    # new filename already exists?
    if data_object.exists(ctx, path_target):
        return api.Error('invalid_destination', 'The selected filename ' + new_file_name + ' already exists')

    # All requirements OK
    try:
        data_object.rename(ctx, coll + '/' + org_file_name, path_target)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


@api.make()
def api_research_file_move(ctx, filepath, new_filepath):
    """Move a file in a research folder.

    :param ctx:          Combined type of a callback and rei struct
    :param filepath:     Path to the file to move
    :param new_filepath: Path to the new location of the file

    :returns: Dict with API status result
    """
    if len(new_filepath) == 0:
        return api.Error('missing_filepath', 'Missing file path. Please add a file path')

    # Same filepath makes no sense.
    if filepath == new_filepath:
        return api.Error('invalid_filepath', 'Origin and move file paths are equal. Please choose another destination')

    coll = pathutil.chop(new_filepath)[0]
    data_name = pathutil.chop(new_filepath)[1]
    try:
        validate_filename(data_name.decode('utf-8'))
    except Exception:
        return api.Error('invalid_filename', 'This is not a valid file name. Please choose another name')

    # not in home - a groupname must be present ie at least 2!?
    if not len(coll.split('/')) > 2:
        return api.Error('invalid_destination', 'It is not possible to move files to this location')

    # Name should not contain '\\' or '/'
    if '/' in data_name or '\\' in data_name:
        return api.Error('invalid_filename', 'It is not allowed to use slashes in the new name of a file')

    # in vault?
    target_group_name = new_filepath.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('invalid_destination', 'It is not possible to move files in the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to move the selected file')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore the indicated file can not be moved')

    # Does org file exist?
    if not data_object.exists(ctx, filepath):
        return api.Error('invalid_source', 'The original file ' + data_name + ' can not be found')

    # new filename already exists?
    if data_object.exists(ctx, new_filepath):
        return api.Error('invalid_destination', 'The file ' + data_name + ' already exists')

    # All requirements OK
    try:
        data_object.rename(ctx, filepath, new_filepath)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


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
        return api.Error('invalid_target', 'It is not possible to delete files at this location')

    # in vault?
    target_group_name = path_target.split('/')[3]
    if target_group_name.startswith('vault-'):
        return api.Error('not_allowed', 'It is not possible to delete files from the vault')

    # permissions ok for group?
    user_full_name = user.full_name(ctx)
    if meta_form.user_member_type(ctx, target_group_name, user_full_name) in ['none', 'reader']:
        return api.Error('not_allowed', 'You do not have sufficient permissions to delete the selected file')

    # Folder not locked?
    if folder.is_locked(ctx, coll):
        return api.Error('not_allowed', 'The indicated folder is locked and therefore the indicated file can not be deleted')

    # Data object exists?
    if not data_object.exists(ctx, path_target):
        return api.Error('invalid_target', 'The data object to delete does not exist')

    # All requirements OK
    try:
        data_object.remove(ctx, path_target)
    except msi.Error as e:
        return api.Error('internal', 'Something went wrong. Please try again')

    return api.Result.ok()


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
