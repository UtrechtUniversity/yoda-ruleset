# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import os
import time

import genquery
import irods_types

import folder
import group
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
           'api_vault_get_package_by_reference',
           'api_vault_copy_to_research',
           'api_vault_get_publication_terms',
           'api_grant_read_access_research_group',
           'api_revoke_read_access_research_group']


@api.make()
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
        research_group_access = collection.exists(ctx, coll_origin)

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
            except Exception:
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
    system_metadata["Data Package Size"] = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

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

    # Data Package Reference.
    data_package_reference = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.DATA_PACKAGE_REFERENCE),
        genquery.AS_LIST, callback
    )

    for row in iter:
        data_package_reference = row[0]
        system_metadata["Data Package Reference"] = "<a href=\"yda/{}\">yda/{}</a>".format(data_package_reference, data_package_reference)

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
        except Exception:
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
        "META_COLL_ATTR_NAME = '" + action_status + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
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
def api_vault_get_package_by_reference(ctx, reference):
    """Return path to data package with provided reference (UUID4).

    :param ctx:       Combined type of a callback and rei struct
    :param reference: Data Package Reference (UUID4)

    :returns: Path to data package.
    """
    data_package = ""
    iter = genquery.row_iterator(
        "COLL_NAME",
        "META_COLL_ATTR_NAME = '{}' and META_COLL_ATTR_VALUE = '{}'".format(constants.DATA_PACKAGE_REFERENCE, reference),
        genquery.AS_LIST, ctx)

    for row in iter:
        data_package = row[0]

    if data_package == "":
        return api.Error('not_found', 'Could not find data package with provided reference.')

    _, _, path, subpath = pathutil.info(data_package)
    return "/{}/{}".format(path, subpath)


@api.make()
def api_vault_get_publication_terms(ctx):
    """Retrieve the publication terms."""
    zone = user.zone(ctx)
    terms_collection = "/{}{}".format(zone, constants.IITERMSCOLLECTION)
    terms = ""

    iter = genquery.row_iterator(
        "DATA_NAME, order_asc(DATA_MODIFY_TIME)",
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


@api.make()
def api_grant_read_access_research_group(ctx, coll):
    """Grant read rights of research group for datapackage in vault.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to remove read rights from

    :returns: API status
    """
    if not collection.exists(ctx, coll):
        return api.Error('DatapackageNotExists', 'Datapackage does not exist')

    coll_parts = coll.split('/')
    if len(coll_parts) != 5:
        return api.Error('InvalidDatapackageCollection', 'Invalid datapackage collection')

    vault_group_name = coll_parts[3]

    # Find category
    group_parts = vault_group_name.split('-')
    research_group_name = 'research-' + '-'.join(group_parts[1:])
    category = meta_form.group_category(ctx, vault_group_name)

    # Is datamanager?
    actor = user.full_name(ctx)
    if meta_form.user_member_type(ctx, 'datamanager-' + category, actor) in ['normal', 'manager']:
        # Grant research group read access to vault package.
        try:
            acl_kv = misc.kvpair(ctx, "actor", actor)
            msi.sudo_obj_acl_set(ctx, "recursive", "read", research_group_name, coll, acl_kv)
        except Exception:
            return api.Error('ErrorACLs', 'Error setting ACLs by datamanager')
    else:
        return api.Error('NoDatamanager', 'Actor must be a datamanager for granting access')

    return {'status': 'Success', 'statusInfo': ''}


@api.make()
def api_revoke_read_access_research_group(ctx, coll):
    """Revoke read rights of research group for datapackage in vault.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to remove read rights from

    :returns: API status
    """
    if not collection.exists(ctx, coll):
        return api.Error('DatapackageNotExists', 'Datapackage does not exist')

    coll_parts = coll.split('/')
    if len(coll_parts) != 5:
        return api.Error('InvalidDatapackageCollection', 'Invalid datapackage collection')

    vault_group_name = coll_parts[3]

    # Find category
    group_parts = vault_group_name.split('-')
    research_group_name = 'research-' + '-'.join(group_parts[1:])
    category = meta_form.group_category(ctx, vault_group_name)

    # Is datamanager?
    actor = user.full_name(ctx)
    if meta_form.user_member_type(ctx, 'datamanager-' + category, actor) in ['normal', 'manager']:
        # Grant research group read access to vault package.
        try:
            acl_kv = misc.kvpair(ctx, "actor", actor)
            msi.sudo_obj_acl_set(ctx, "recursive", "null", research_group_name, coll, acl_kv)
        except Exception:
            return api.Error('ErrorACLs', 'Error setting ACLs by datamanager')
    else:
        return api.Error('NoDatamanager', 'Actor must be a datamanager for revoking access')

    return {'status': 'Success', 'statusInfo': ''}


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
        except msi.Error:
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
        except msi.Error:
            return 1

        if markIncomplete:
            avu.set_on_coll(ctx, dest_path, constants.IIVAULTSTATUSATTRNAME, constants.vault_package_state.INCOMPLETE)
    else:
        # CREATE COPY OF DATA OBJECT
        try:
            # msi.data_obj_copy(ctx, source_path, dest_path, '', irods_types.BytesBuf())
            ctx.msiDataObjCopy(source_path, dest_path, 'verifyChksum=', 0)
        except msi.Error:
            return 1

    if read_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), source_path)
        except msi.Error:
            return 1

    return 0


def set_vault_permissions(ctx, group_name, folder, target):
    """Set permissions in the vault as such that data can be copied to the vault."""
    parts = group_name.split('-')
    base_name = '-'.join(parts[1:])

    parts = folder.split('/')
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
            except msi.Error:
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
        return ['Success', '']
    except msi.Error:
        current_coll_status = get_coll_vault_status(ctx, coll).value
        is_legal = policies_datapackage_status.can_transition_datapackage_status(ctx, actor, coll, current_coll_status, new_coll_status)
        if not is_legal:
            return ['1', 'Illegal status transition']
        else:
            if new_coll_status == str(constants.vault_package_state.PUBLISHED):
                # Special case is transition to PUBLISHED
                # landing page and doi have to be present

                # Landingpage URL.
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
            "META_COLL_ATTR_NAME = '" + action_status + "' AND META_COLL_ATTR_VALUE = 'PENDING'",
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


def set_submitter(ctx, path, actor):
    """Set submitter of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_submission_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_submitter(ctx, path):
    """Set submitter of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_submission_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return None


def set_approver(ctx, path, actor):
    """Set approver of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_approval_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_approver(ctx, path):
    """Set approver of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_approval_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return None
