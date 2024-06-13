# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import os
import re
import subprocess
import time
from datetime import datetime

import genquery
import irods_types
from dateutil import parser

import folder
import groups
import meta
import meta_form
import policies_datamanager
import policies_datapackage_status
from util import *

__all__ = ['api_vault_submit',
           'api_vault_approve',
           'api_vault_cancel',
           'api_vault_depublish',
           'api_vault_republish',
           'api_vault_preservable_formats_lists',
           'api_vault_unpreservable_files',
           'rule_vault_copy_to_vault',
           'rule_vault_copy_numthreads',
           'rule_vault_copy_original_metadata_to_vault',
           'rule_vault_write_license',
           'rule_vault_enable_indexing',
           'rule_vault_disable_indexing',
           'rule_vault_process_status_transitions',
           'api_vault_system_metadata',
           'api_vault_collection_details',
           'api_vault_get_package_by_reference',
           'api_vault_copy_to_research',
           'api_vault_get_publication_terms',
           'api_vault_get_landingpage_data',
           'api_grant_read_access_research_group',
           'api_revoke_read_access_research_group',
           'api_vault_get_published_packages']


@api.make()
def api_vault_submit(ctx, coll, previous_version=None):
    """Submit data package for publication.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Collection of data package to submit
    :param previous_version: Path to previous version of data package in the vault

    :returns: API status
    """
    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.SUBMITTED_FOR_PUBLICATION, previous_version)

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
    # Check for previous version.
    previous_version = get_previous_version(ctx, coll)

    # Add related data package metadata for new and previous version.
    if previous_version:
        meta_add_new_version(ctx, coll, previous_version)

    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.APPROVED_FOR_PUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_approve: iiAdminVaultActions')
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
        return api.Error('HomeCollectionNotAllowed', 'Please select a specific research folder for your datapackage')

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
    category = groups.group_category(ctx, group_name)
    is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))

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
    if not groups.user_role(ctx, user_full_name, group_name) in ['normal', 'manager']:
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

    # Exclude Yoda metadata files
    data_names = itertools.ifilter(lambda
                                   x: not re.match(r"yoda\-metadata(\[\d+\])?\.(xml|json)", x),
                                   data_names)

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


def get_vault_copy_numthreads(ctx):
    # numThreads should be 0 if want multithreading with no specified amount of threads
    return 0 if config.vault_copy_multithread_enabled else 1


def vault_copy_original_metadata_to_vault(ctx, vault_package_path):
    """Copy original metadata to the vault package root.

    :param ctx:  Combined type of a callback and rei struct
    :param vault_package_path: Path of a package in the vault
    """
    original_metadata = vault_package_path + "/original/" + constants.IIJSONMETADATA
    copied_metadata = vault_package_path + '/yoda-metadata[' + str(int(time.time())) + '].json'

    # Copy original metadata JSON.
    ctx.msiDataObjCopy(original_metadata, copied_metadata, 'destRescName={}++++numThreads={}++++verifyChksum='.format(config.resource_vault, get_vault_copy_numthreads(ctx)), 0)

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
            data_object.remove(ctx, license_file, force=True)
    else:
        # License set in user metadata, a License.txt should exist in package.
        # Check if license text exists.
        license_txt = "/{}{}/{}.txt".format(zone, constants.IILICENSECOLLECTION, license)
        if data_object.exists(ctx, license_txt):
            # Copy license file.
            license_file = vault_pkg_coll + "/License.txt"
            ctx.msiDataObjCopy(license_txt, license_file, 'destRescName={}++++forceFlag=++++numThreads={}++++verifyChksum='.format(config.resource_vault, get_vault_copy_numthreads(ctx)), 0)

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


@rule.make(inputs=[0], outputs=[1])
def rule_vault_enable_indexing(ctx, coll):
    vault_enable_indexing(ctx, coll)
    return "Success"


def vault_enable_indexing(ctx, coll):
    if config.enable_open_search:
        if not collection.exists(ctx, coll + "/index"):
            # index collection does not exist yet
            path = meta.get_latest_vault_metadata_path(ctx, coll)
            ctx.msi_rmw_avu('-d', path, '%', '%', constants.UUFLATINDEX)
            meta.ingest_metadata_vault(ctx, path)

        # add indexing attribute and update opensearch
        subprocess.call(["imeta", "add", "-C", coll + "/index", "irods::indexing::index", "yoda::metadata", "elasticsearch"])


@rule.make(inputs=[0], outputs=[1])
def rule_vault_disable_indexing(ctx, coll):
    vault_disable_indexing(ctx, coll)
    return "Success"


def vault_disable_indexing(ctx, coll):
    if config.enable_open_search:
        if collection.exists(ctx, coll + "/index"):
            coll = coll + "/index"

        # tricky: remove indexing attribute without updating opensearch
        try:
            msi.mod_avu_metadata(ctx, "-C", coll, "rm", "irods::indexing::index", "yoda::metadata", "elasticsearch")
        except Exception:
            pass


@api.make()
def api_vault_system_metadata(ctx, coll):
    """Return system metadata of a vault collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package

    :returns: Dict system metadata of a vault collection
    """
    system_metadata = {}

    # Package size.
    data_count = collection.data_count(ctx, coll)
    collection_count = collection.collection_count(ctx, coll)
    size = collection.size(ctx, coll)
    size_readable = misc.human_readable_size(size)
    system_metadata["Data Package Size"] = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    # Modified date.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_lastModifiedDateTime'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
        # modified_date = date.fromisoformat(row[0])
        modified_date = parser.parse(row[0])
        modified_date = modified_date.strftime('%Y-%m-%d %H:%M:%S%z')
        system_metadata["Modified date"] = "{}".format(modified_date)

    # Landingpage URL.
    landinpage_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_landingPageUrl'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        landinpage_url = row[0]
        system_metadata["Landingpage"] = "<a href=\"{}\">{}</a>".format(landinpage_url, landinpage_url)

    # Check for previous version.
    previous_version = get_previous_version(ctx, coll)
    if previous_version:
        previous_version_doi = get_doi(ctx, previous_version)
        system_metadata["Persistent Identifier DOI"] = persistent_identifier_doi = "previous version: <a href=\"https://doi.org/{}\">{}</a>".format(previous_version_doi, previous_version_doi)

    # Persistent Identifier DOI.
    package_doi = get_doi(ctx, coll)

    if package_doi:
        if previous_version:
            persistent_identifier_doi = "<a href=\"https://doi.org/{}\">{}</a> (previous version: <a href=\"https://doi.org/{}\">{}</a>)".format(package_doi, package_doi, previous_version_doi, previous_version_doi)
        else:
            persistent_identifier_doi = "<a href=\"https://doi.org/{}\">{}</a>".format(package_doi, package_doi)
        system_metadata["Persistent Identifier DOI"] = persistent_identifier_doi

    # Data Package Reference.
    data_package_reference = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.DATA_PACKAGE_REFERENCE),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        data_package_reference = row[0]
        system_metadata["Data Package Reference"] = "<a href=\"yoda/{}\">yoda/{}</a>".format(data_package_reference, data_package_reference)

    # Persistent Identifier EPIC.
    package_epic_pid = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_pid'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        package_epic_pid = row[0]

    package_epic_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_url'" % (coll),
        genquery.AS_LIST, ctx
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
    """Return details of a vault collection.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to data package

    :returns: Dict with collection details
    """
    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is a research group.
    space, _, group, subpath = pathutil.info(path)
    if space != pathutil.Space.VAULT:
        return {}

    basename = pathutil.basename(path)

    # Find group name to retrieve member type
    group_parts = group.split('-')
    if subpath.startswith("deposit-"):
        research_group_name = 'deposit-' + '-'.join(group_parts[1:])
    else:
        research_group_name = 'research-' + '-'.join(group_parts[1:])

    member_type = groups.user_role(ctx, user.full_name(ctx), research_group_name)

    # Retrieve vault folder status.
    status = get_coll_vault_status(ctx, path).value

    # Check if collection has datamanager.
    has_datamanager = True

    # Check if user is datamanager.
    category = groups.group_category(ctx, group)
    is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))

    # Check if collection is vault package.
    metadata_path = meta.get_latest_vault_metadata_path(ctx, path)
    if metadata_path is None:
        return {'member_type': member_type, 'is_datamanager': is_datamanager}
    else:
        metadata = True

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
            if user_name.startswith(("research-", "deposit-")):
                research_group_access = True

    result = {
        "basename": basename,
        "status": status,
        "metadata": metadata,
        "member_type": member_type,
        "has_datamanager": has_datamanager,
        "is_datamanager": is_datamanager,
        "vault_action_pending": vault_action_pending,
        "research_group_access": research_group_access
    }
    if config.enable_data_package_archive:
        import vault_archive
        result["archive"] = {
            "archivable": vault_archive.vault_archivable(ctx, path),
            "status": vault_archive.vault_archival_status(ctx, path)
        }
    if config.enable_data_package_download:
        import vault_download
        result["downloadable"] = vault_download.vault_downloadable(ctx, path)
    return result


@api.make()
def api_vault_get_package_by_reference(ctx, reference):
    """Return path to data package with provided reference (UUID4).

    :param ctx:       Combined type of a callback and rei struct
    :param reference: Data Package Reference (UUID4)

    :returns: Path to data package
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
def api_vault_get_landingpage_data(ctx, coll):
    """Retrieve landingpage data of data package.

    Landinpage data consists of metadata and system metadata.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to retrieve landingpage data from

    :returns: API status
    """
    meta_path = meta.get_latest_vault_metadata_path(ctx, coll)

    # Try to load the metadata file.
    try:
        metadata = jsonutil.read(ctx, meta_path)
        current_schema_id = meta.metadata_get_schema_id(metadata)
        if current_schema_id is None:
            return api.Error('no_schema_id', 'Please check the structure of this file.',
                             'schema id missing')
    except jsonutil.ParseError:
        return api.Error('bad_json', 'Please check the structure of this file.', 'JSON invalid')
    except msi.Error as e:
        return api.Error('internal', 'The metadata file could not be read.', e)

    # Get deposit date and end preservation date based upon retention period
    # "submitted for vault"
    # deposit_date = '2016-02-29'  # To be gotten from the action log
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[1])
        if log_item_list[1] == "submitted for vault":
            deposit_timestamp = datetime.fromtimestamp(int(log_item_list[0]))
            deposit_date = deposit_timestamp.strftime('%Y-%m-%d')
            break

    return {'metadata': metadata, 'deposit_date': deposit_date}


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
        return api.Error('nonexistent', 'The given path does not exist')

    coll_parts = coll.split('/')
    if len(coll_parts) != 5:
        return api.Error('invalid_collection', 'The datamanager can only revoke permissions to vault packages')

    space, zone, group, subpath = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return api.Error('invalid_collection', 'The datamanager can only revoke permissions to vault packages')

    # Find category
    group_parts = group.split('-')
    if subpath.startswith("deposit-"):
        research_group_name = 'deposit-' + '-'.join(group_parts[1:])
    else:
        research_group_name = 'research-' + '-'.join(group_parts[1:])
    category = groups.group_category(ctx, group)

    # Is datamanager?
    actor = user.full_name(ctx)
    if groups.user_role(ctx, actor, 'datamanager-' + category) in ['normal', 'manager']:
        # Grant research group read access to vault package.
        try:
            acl_kv = msi.kvpair(ctx, "actor", actor)
            msi.sudo_obj_acl_set(ctx, "recursive", "read", research_group_name, coll, acl_kv)
        except Exception:
            policy_error = policies_datamanager.can_datamanager_acl_set(ctx, coll, actor, research_group_name, "1", "read")
            if bool(policy_error):
                return api.Error('ErrorACLs', 'Could not acquire datamanager access to {}.'.format(coll))
            else:
                return api.Error('ErrorACLs', str(policy_error))
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
        return api.Error('nonexistent', 'The given path does not exist')

    coll_parts = coll.split('/')
    if len(coll_parts) != 5:
        return api.Error('invalid_collection', 'The datamanager can only revoke permissions to vault packages')

    space, zone, group, subpath = pathutil.info(coll)
    if space != pathutil.Space.VAULT:
        return api.Error('invalid_collection', 'The datamanager can only revoke permissions to vault packages')

    # Find category
    group_parts = group.split('-')
    if subpath.startswith("deposit-"):
        research_group_name = 'deposit-' + '-'.join(group_parts[1:])
    else:
        research_group_name = 'research-' + '-'.join(group_parts[1:])
    category = groups.group_category(ctx, group)

    # Is datamanager?
    actor = user.full_name(ctx)
    if groups.user_role(ctx, actor, 'datamanager-' + category) in ['normal', 'manager']:
        # Grant research group read access to vault package.
        try:
            acl_kv = msi.kvpair(ctx, "actor", actor)
            msi.sudo_obj_acl_set(ctx, "recursive", "null", research_group_name, coll, acl_kv)
        except Exception:
            policy_error = policies_datamanager.can_datamanager_acl_set(ctx, coll, actor, research_group_name, "1", "read")
            if bool(policy_error):
                return api.Error('ErrorACLs', 'Could not acquire datamanager access to {}.'.format(coll))
            else:
                return api.Error('ErrorACLs', str(policy_error))
    else:
        return api.Error('NoDatamanager', 'Actor must be a datamanager for revoking access')

    return {'status': 'Success', 'statusInfo': ''}


@rule.make()
def rule_vault_copy_to_vault(ctx, state):
    """ Collect all folders with a given cronjob state
        and try to copy them to the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param state: one of constants.CRONJOB_STATE
    """
    iter = get_copy_to_vault_colls(ctx, state)
    for row in iter:
        coll = row[0]
        log.write(ctx, "copy_to_vault {}: {}".format(state, coll))
        if not folder.precheck_folder_secure(ctx, coll):
            continue

        # failed copy
        if not folder.folder_secure(ctx, coll):
            log.write(ctx, "copy_to_vault {} failed for collection <{}>".format(state, coll))
            folder.folder_secure_set_retry(ctx, coll)


def get_copy_to_vault_colls(ctx, cronjob_state):
    iter = list(genquery.Query(ctx,
                ['COLL_NAME'],
                "META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}'".format(
                    constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault",
                    cronjob_state),
                output=genquery.AS_LIST))
    return iter


def copy_folder_to_vault(ctx, coll, target):
    """Copy folder and all its contents to target in vault using irsync.

    The data will reside under folder '/original' within the vault.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Path of a folder in the research space
    :param target: Path of a package in the vault space

    :returns: True for successful copy
    """
    returncode = 0
    try:
        returncode = subprocess.call(["irsync", "-rK", "i:{}/".format(coll), "i:{}/original".format(target)])
    except Exception as e:
        log.write(ctx, "irsync failure: " + e)
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    if returncode != 0:
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    return True


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

    # TODO use set_acl_check?
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
            ctx.msiDataObjCopy(source_path, dest_path, 'numThreads={}++++verifyChksum='.format(get_vault_copy_numthreads(ctx)), 0)
        except msi.Error:
            return 1

    if read_access != b'\x01':
        try:
            msi.set_acl(ctx, "default", "admin:null", user.full_name(ctx), source_path)
        except msi.Error:
            return 1

    return 0


def set_vault_permissions(ctx, coll, target):
    """Set permissions in the vault as such that data can be copied to the vault."""
    group_name = folder.collection_group_name(ctx, coll)
    if group_name == '':
        log.write(ctx, "set_vault_permissions: Cannot determine which deposit or research group <{}> belongs to".format(coll))
        return False

    parts = group_name.split('-')
    base_name = '-'.join(parts[1:])

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

    return True


@rule.make(inputs=range(4), outputs=range(4, 6))
def rule_vault_process_status_transitions(ctx, coll, new_coll_status, actor, previous_version):
    """Rule interface for processing vault status transition request.

    :param ctx:             Combined type of a callback and rei struct
    :param coll:            Vault collection to change status for
    :param new_coll_status: New vault package status
    :param actor:           Actor of the status change
    :param previous_version: Path to previous version of data package in the vault

    :return: Dict with status and statusinfo.
    """
    vault_process_status_transitions(ctx, coll, new_coll_status, actor, previous_version)

    return 'Success'


def vault_process_status_transitions(ctx, coll, new_coll_status, actor, previous_version):
    """Processing vault status transition request.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault collection to change status for
    :param new_coll_status:  New vault package status
    :param actor:            Actor of the status change
    :param previous_version: Path to previous version of data package in the vault

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
        if previous_version:
            avu.set_on_coll(ctx, coll, "org_publication_previous_version", previous_version)

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
                    "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_versionDOI'" % (coll),
                    genquery.AS_LIST, callback
                )

                for row in iter:
                    if row[0] == "":
                        return ['1', 'DOI is missing']

    return ['Success', '']


def vault_request_status_transitions(ctx, coll, new_vault_status, previous_version=None):
    """Request vault status transition action.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault package to be changed of status in publication cycle
    :param new_vault_status: New vault status
    :param previous_version: Path to previous version of data package in the vault

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

    zone = user.zone(ctx)
    coll_parts = coll.split('/')
    vault_group_name = coll_parts[3]

    # Find actor and actor group.
    actor = user.full_name(ctx)
    actor_group = folder.collection_group_name(ctx, coll)
    if actor_group == '':
        log.write(ctx, "Cannot determine which research group " + coll + " belongs to")
        return ['1', '']
    actor_group_path = '/' + zone + '/home/'

    # Check if user is datamanager.
    category = groups.group_category(ctx, vault_group_name)
    is_datamanager = groups.user_is_datamanager(ctx, category, user.full_name(ctx))

    # Status SUBMITTED_FOR_PUBLICATION can only be requested by researcher.
    # Status UNPUBLISHED can be called by researcher and datamanager.
    if not is_datamanager:
        if new_vault_status in [constants.vault_package_state.SUBMITTED_FOR_PUBLICATION, constants.vault_package_state.UNPUBLISHED]:
            actor_group_path = '/' + zone + '/home/' + actor_group
    else:
        actor_group_path = '/' + zone + '/home/datamanager-' + category

    # Retrieve collection id.
    coll_id = collection.id_from_name(ctx, coll)

    # Check if vault package is currently pending for status transition.
    # Except for status transition to PUBLISHED/DEPUBLISHED,
    # because it is requested by the system before previous pending
    # transition is removed.
    if new_vault_status not in (constants.vault_package_state.PUBLISHED, constants.vault_package_state.DEPUBLISHED):
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

    # Data package is new version of existing data package with a DOI.
    previous_version_path = ""
    doi = get_doi(ctx, previous_version)
    if previous_version and doi:
        previous_version_path = previous_version

    # Add vault action request to actor group.
    avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'vault_action_' + coll_id, jsonutil.dump([coll, str(new_vault_status), actor, previous_version_path]))
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


def get_doi(ctx, path):
    """Get the DOI of a data package in the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Vault package to get the DOI of

    :return: Data package DOI or None
    """
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_versionDOI'" % (path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_previous_version(ctx, path):
    """Get the previous version of a data package in the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Vault package to get the previous version of

    :return: Data package path or None
    """
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_previous_version'" % (path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_title(ctx, path):
    """Get the title of a data package in the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Vault package to get the title of

    :return: Data package title
    """
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'Title' AND META_COLL_ATTR_UNITS = 'usr_0_s'" % (path),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return "(no title)"


def meta_add_new_version(ctx, new_version, previous_version):
    """Add new version as related resource metadata to data package in a vault.

    :param ctx:              Combined type of a callback and rei struct
    :param new_version:      Path to new version of data package in the vault
    :param previous_version: Path to previous version of data package in the vault
    """
    form = meta_form.load(ctx, new_version)
    schema = form["schema"]
    metadata = form["metadata"]

    # Only add related data package if it is in the schema.
    if "Related_Datapackage" in schema["properties"]:
        data_package = {
            "Persistent_Identifier": {
                "Identifier_Scheme": "DOI",
                "Identifier": "https://doi.org/{}".format(get_doi(ctx, previous_version))
            },
            "Relation_Type": "IsNewVersionOf",
            "Title": "{}".format(get_title(ctx, previous_version))
        }

        if "Related_Datapackage" in metadata:
            metadata["Related_Datapackage"].append(data_package)
        else:
            metadata["Related_Datapackage"] = [data_package]

        meta_form.save(ctx, new_version, metadata)

    # Only add related resource if it is in the schema.
    elif "Related_Resource" in schema["properties"]:
        data_package = {
            "Persistent_Identifier": {
                "Identifier_Scheme": "DOI",
                "Identifier": "https://doi.org/{}".format(get_doi(ctx, previous_version))
            },
            "Relation_Type": "IsNewVersionOf",
            "Title": "{}".format(get_title(ctx, previous_version))
        }

        if "Related_Resource" in metadata:
            metadata["Related_Resource"].append(data_package)
        else:
            metadata["Related_Resource"] = [data_package]

        meta_form.save(ctx, new_version, metadata)


def get_all_doi_versions(ctx, path):
    """Get the path and DOI of latest versions of published data package in a vault.

    :param ctx:     Combined type of a callback and rei struct
    :param path:    Path of vault with data packages

    :return: Dict of data packages with DOI
    """

    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, GROUP(COLL_NAME)",
        "COLL_PARENT_NAME = '{}' AND META_COLL_ATTR_NAME IN ('org_publication_versionDOI', 'org_publication_baseDOI', 'org_publication_publicationDate')".format(path),
        genquery.AS_LIST, ctx
    )

    data_packages = []
    org_publ_info = []

    for row in iter:
        org_publ_info.append([row[0], row[1], row[2]])

    # Group by collection name
    coll_names = set(map(lambda x: x[2], org_publ_info))
    grouped_coll_name = [[y[1] for y in org_publ_info if y[2] == x] + [x] for x in coll_names]

    # If base DOI does not exist, remove from the list and add it in the data package
    number_of_items = list(map(len, grouped_coll_name))
    indices = [i for i, x in enumerate(number_of_items) if x < 4]

    for item in indices:
        data_packages.append([0] + grouped_coll_name[item])

    grouped_coll_name = [grouped_coll_name[i] for i, e in enumerate(grouped_coll_name) if i not in indices]

    # Group by base DOI
    base_dois = set(map(lambda x: x[0], grouped_coll_name))
    grouped_base_dois = [[y for y in grouped_coll_name if y[0] == x] for x in base_dois]

    return org_publ_info, data_packages, grouped_base_dois


@api.make()
def api_vault_get_published_packages(ctx, path):
    """Get the path and DOI of latest versions of published data package in a vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of vault with data packages

    :return: Dict of data packages with DOI
    """

    org_publ_info, data_packages, grouped_base_dois = get_all_doi_versions(ctx, path)

    # Sort by publication date
    sorted_publ = [sorted(x, key=lambda x: datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f")) for x in grouped_base_dois]

    latest_publ = map(lambda x: x[-1], sorted_publ)

    # Append to data package
    for items in latest_publ:
        data_packages.append(items)

    # Retrieve title of data packages.
    published_packages = {}
    for item in data_packages:
        published_packages[item[2]] = {"path": item[3], "title": get_title(ctx, item[3])}

    return published_packages


def update_archive(ctx, coll, attr=None):
    """Potentially update archive after metadata changed.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package
    :param attr: The AVU that was changed, if any
    """
    if config.enable_data_package_archive:
        import vault_archive

        vault_archive.update(ctx, coll, attr)


@rule.make(inputs=[], outputs=[0])
def rule_vault_copy_numthreads(ctx):
    return get_vault_copy_numthreads(ctx)
