"""Functions to copy packages to the vault and manage permissions of vault packages."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple

import genquery
from dateutil import parser

import folder
import groups
import meta
import meta_form
import notifications
import policies_datamanager
import policies_datapackage_status
import vault_deaccession
from util import *
from vault_utils import get_copy_irsync_command, get_sanity_checks_results_copy_to_research_paths, get_sanity_checks_results_copy_to_vault_paths

__all__ = ['api_vault_submit',
           'api_vault_approve',
           'api_vault_cancel',
           'api_vault_depublish',
           'api_vault_republish',
           'api_vault_preservable_formats_lists',
           'api_vault_unpreservable_files',
           'rule_vault_copy_to_research',
           'rule_vault_copy_to_vault',
           'rule_vault_copy_numthreads',
           'rule_vault_copy_original_metadata_to_vault',
           'rule_vault_write_license',
           'rule_vault_enable_indexing',
           'rule_vault_disable_indexing',
           'rule_vault_process_status_transitions',
           'rule_vault_grant_readers_vault_access',
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
def api_vault_submit(ctx: rule.Context, coll: str, previous_version: str | None = None) -> api.Result:
    """Submit data package for publication.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Collection of data package to submit
    :param previous_version: Path to previous version of data package in the vault

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.SUBMITTED_FOR_PUBLICATION, previous_version)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_approve(ctx: rule.Context, coll: str) -> api.Result:
    """Approve data package for publication.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to approve

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

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
def api_vault_cancel(ctx: rule.Context, coll: str) -> api.Result:
    """Cancel submit of data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to cancel submit

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.UNPUBLISHED)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_depublish(ctx: rule.Context, coll: str) -> api.Result:
    """Depublish data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to depublish

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.PENDING_DEPUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_republish(ctx: rule.Context, coll: str) -> api.Result:
    """Republish data package.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to republish

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    ret = vault_request_status_transitions(ctx, coll, constants.vault_package_state.PENDING_REPUBLICATION)

    if ret[0] == '':
        log.write(ctx, 'api_vault_submit: iiAdminVaultActions')
        ctx.iiAdminVaultActions()
        return 'Success'
    else:
        return api.Error(ret[0], ret[1])


@api.make()
def api_vault_copy_to_research(ctx: rule.Context, coll_origin: str, coll_target: str) -> api.Result:
    """Copy data package from vault to research space.

    :param ctx:         Combined type of a callback and rei struct
    :param coll_origin: Collection of data package to copy
    :param coll_target: Collection to copy data package to

    :returns: API status
    """
    coll_target = coll_target.rstrip('/')
    coll_origin = coll_origin.rstrip('/')

    # Validate origin location.
    space, _, _, _ = pathutil.info(coll_origin)
    if space is not pathutil.Space.VAULT:
        return api.Error('RequiredVaultOrigin', 'Please select a specific vault datapackage to copy')

    # Validate target location.
    space, _, group_name, _ = pathutil.info(coll_target)
    if space is not pathutil.Space.RESEARCH:
        return api.Error('RequiredIsResearchArea', 'Please select a specific research folder for your datapackage')

    # Concatenate coll_target with package name to create sub_coll_target.
    _, package_name = pathutil.chop(coll_origin)
    sub_coll_target = f'{coll_target}/{package_name}'

    # Verify target collection exists (parent of sub_coll_target).
    if not collection.exists(ctx, coll_target):
        return api.Error('TargetPathNotExists', 'The target you specified does not exist')

    # Verify sub_coll_target package NOT already exists.
    if collection.exists(ctx, sub_coll_target):
        return api.Error('PackageAlreadyPresentInTarget', 'This datapackage is already present at the specified location')

    # Check user permissions.
    user_full_name = user.full_name(ctx)
    category       = groups.group_category(ctx, group_name)
    is_datamanager = groups.user_is_datamanager(ctx, category, user_full_name)

    if not is_datamanager and not collection.exists(ctx, coll_origin):
        return api.Error('NoPermissions', 'Insufficient rights to perform this action')

    # Check for possible locks on target collection.
    lock_count = meta_form.get_coll_lock_count(ctx, coll_target)
    if lock_count:
        return api.Error('TargetCollectionLocked', 'The folder you selected is locked.')

    # Check if user has write access to research folder.
    # Only normal user has write access.
    user_role = groups.user_role(ctx, user_full_name, group_name)
    if user_role not in ['normal', 'manager']:
        return api.Error('NoWriteAccessTargetCollection', 'Not permitted to write in selected folder')

    # Register to delayed rule queue.
    retry_count  = 1
    wait_seconds = 0
    schedule_copy_to_research(ctx, coll_origin, sub_coll_target, user_full_name, retry_count, wait_seconds)

    return {
        "status": "ok",
        "target": sub_coll_target,
        "origin": coll_origin
    }


def schedule_copy_to_research(ctx: rule.Context, coll_origin: str, coll_target: str, actor: str, retry_count: int, wait_seconds: int) -> None:
    """
    A help function to call `msiExecCmd("admin-copy-to-research.sh", …)` job
    through the delay server.

    :param ctx:          Combined type of a callback and rei struct
    :param coll_origin:  Origin data collection in vault space
    :param coll_target:  Target collection path in research space
    :param actor:        User to notify of success/failure
    :param retry_count:  Current retry attempt as int
    :param wait_seconds: Delay in seconds
    """
    ctx.delayExec(
        f"<PLUSET>{wait_seconds}s</PLUSET>",
        f"iiAdminVaultCopyToResearch('{coll_origin}', '{coll_target}', '{actor}', '{retry_count}')",
        "")


@rule.make(inputs=[0, 1, 2, 3], outputs=[])
def rule_vault_copy_to_research(ctx: rule.Context, coll_origin: str, coll_target: str, actor: str, retry_str: str) -> None:
    """Orchestrate vault copy-to-research operation with retry handling.
    If the copy operation fails, it will be retried up to a maximum number of times.

    :param ctx:         Combined type of a callback and rei struct
    :param coll_origin: Origin data collection in vault space
    :param coll_target: Target collection in research or deposit space
    :param actor:       User to notify of success/failure
    :param retry_str:   Current retry attempt as string

    :returns:           True if operation succeeded or entered retry logic, False if target already existed
    """
    log.write(ctx, f"Starting vault copy: {coll_origin} -> {coll_target}, attempt #{retry_str}")

    space, _, _, _ = pathutil.info(coll_target)

    # Check target already existed during the retry process, to prevent double clicking
    if space is pathutil.Space.RESEARCH and collection.exists(ctx, coll_target):
        log.write(ctx, f"Target collection already exists: {coll_target}")
        return None

    # Execute copy operation through irsync cmd
    success = copy_folder_to_research(ctx, coll_origin, coll_target)

    # Handle result
    if success:
        # Fix ACLs for data package copied to deposit.
        if space is pathutil.Space.DEPOSIT:
            msi.set_acl(ctx, "recursive", "admin:own", actor, coll_target)

        _, _, _, datapackage_name = pathutil.info(coll_origin)
        notifications.set(ctx, "system", actor, coll_target, f"Copying data package <{datapackage_name}>finished")
        log.write(ctx, f"Copy successful: {coll_origin}")
    else:
        # Copy failed and enter retry logic
        retry_count = int(retry_str)
        handle_retry_operation(ctx, coll_origin, coll_target, actor, retry_count)


def copy_folder_to_research(ctx: rule.Context, coll: str, target: str) -> bool:
    """Copy vault data package and all its contents to target in research using irsync.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Path of a folder in the vault space
    :param target: Path of a package in the research space

    :returns: True for successful copy
    """
    sanity_check_results = get_sanity_checks_results_copy_to_research_paths(coll, target)
    if len(sanity_check_results) > 0:
        log.write(ctx, "Not copying folder to research because of sanity check failures: "
                  + str(sanity_check_results))
        return False

    admin = user.full_name(ctx)
    parent, _ = pathutil.chop(target)
    msi.set_acl(ctx, "recursive", "admin:write", admin, parent)

    returncode = 0
    irsync_command = get_copy_irsync_command(coll,
                                             target,
                                             config.resource_vault,
                                             config.vault_copy_multithread_enabled)

    try:
        returncode = subprocess.call(irsync_command)
    except Exception as e:
        log.write(ctx, "irsync failure: " + str(e))
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    if returncode != 0:
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    return True


def handle_retry_operation(ctx: rule.Context, coll_origin: str, coll_target: str, actor: str, retry_count: int) -> bool:
    """Manage retry logic with delays for copy-to-research workflow

    :param ctx:         Combined type of a callback and rei struct
    :param coll_origin: Origin data collection in vault space
    :param coll_target: Target data collection in research space
    :param actor:       User to notify of success/failure
    :param retry_count: Current retry attempt as integer

    :returns:           True if retry scheduled, False if max retries exceeded or scheduling failed
    """
    log.write(ctx, f"Copy failed: {coll_origin} for {actor}, entering retry logic, attempt #{retry_count}")

    max_retries = config.vault_copy_max_retries
    wait_seconds = config.vault_copy_backoff_time  # in seconds

    if retry_count >= max_retries:
        _, _, _, datapackage_name = pathutil.info(coll_origin)
        log.write(ctx, f"Max retries exceeded for copy_to_research: {coll_origin}")
        notifications.set(ctx, "system", actor, coll_origin, "Copying data package <{datapackage_name}> failed, max retries exceeded")
        return False

    next_attempt  = retry_count + 1
    log.write(ctx, f"Scheduled attempt #{next_attempt} in {wait_seconds}s for: {coll_origin}")

    # one single call, identical path through the delay server
    schedule_copy_to_research(ctx, coll_origin, coll_target, actor, next_attempt, wait_seconds)

    return True


@api.make()
def api_vault_preservable_formats_lists(ctx: rule.Context) -> api.Result:
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
def api_vault_unpreservable_files(ctx: rule.Context, coll: str, list_name: str) -> api.Result:
    """Retrieve list of unpreservable file formats in a collection.

    :param ctx:       Combined type of a callback and rei struct
    :param coll:      Collection of folder to check
    :param list_name: Name of preservable file format list

    :returns: List of unpreservable file formats
    """
    space, zone, _, _ = pathutil.info(coll)
    if space not in [pathutil.Space.RESEARCH, pathutil.Space.VAULT]:
        return api.Error('invalid_path', 'Invalid vault path.')

    # Retrieve JSON list of preservable file formats.
    list_data = jsonutil.read(ctx, '/{}/yoda/file_formats/{}.json'.format(zone, list_name))
    preservable_formats = set(list_data['formats'])

    # Get basenames of all data objects within this collection.
    data_names = (pathutil.chop(x)[1] for x in collection.data_objects(ctx, coll, recursive=True))

    # Exclude Yoda metadata files
    data_names_filtered = filter(lambda x: not re.match(r"yoda\-metadata(\[\d+\])?\.(xml|json)", x), data_names)

    # Data names -> lowercase extensions, without the dot.
    exts  = {os.path.splitext(x)[1][1:].lower() for x in data_names_filtered}
    exts -= {''}

    # Return any ext that is not in the preservable list.
    return list(exts - preservable_formats)


@rule.make(inputs=[0], outputs=[])
def rule_vault_copy_original_metadata_to_vault(ctx: rule.Context, vault_package: str) -> None:
    """Copy the original metadata JSON into the root of the package.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path of a package in the vault
    """
    vault_copy_original_metadata_to_vault(ctx, vault_package)


def get_vault_copy_numthreads(ctx: rule.Context) -> int:
    # numThreads should be 0 if want multithreading with no specified amount of threads
    return 0 if config.vault_copy_multithread_enabled else 1


def vault_copy_original_metadata_to_vault(ctx: rule.Context, vault_package_path: str) -> None:
    """Copy original metadata to the vault package root.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package_path: Path of a package in the vault
    """
    original_metadata = vault_package_path + "/original/" + constants.IIJSONMETADATA
    copied_metadata = vault_package_path + '/yoda-metadata[' + str(int(time.time())) + '].json'

    # Copy original metadata JSON.
    ctx.msiDataObjCopy(original_metadata, copied_metadata, 'destRescName={}++++numThreads={}++++verifyChksum='.format(config.resource_vault, get_vault_copy_numthreads(ctx)), 0)

    # msi.data_obj_copy(ctx, original_metadata, copied_metadata, 'verifyChksum=', irods_types.BytesBuf())


@rule.make(inputs=[0], outputs=[])
def rule_vault_write_license(ctx: rule.Context, vault_pkg_coll: str) -> None:
    """Write the license as a text file into the root of the vault package.

    :param ctx:            Combined type of a callback and rei struct
    :param vault_pkg_coll: Path of a package in the vault
    """
    vault_write_license(ctx, vault_pkg_coll)


def vault_write_license(ctx: rule.Context, vault_pkg_coll: str) -> None:
    """Write the license as a text file into the root of the vault package.

    :param ctx:            Combined type of a callback and rei struct
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
                copy_acls_from_parent(ctx, license_file, "default")
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
def rule_vault_enable_indexing(ctx: rule.Context, coll: str) -> str:
    vault_enable_indexing(ctx, coll)
    return "Success"


def vault_enable_indexing(ctx: rule.Context, coll: str) -> None:
    if config.enable_open_search:
        if not collection.exists(ctx, coll + "/index"):
            # index collection does not exist yet
            path = meta.get_latest_vault_metadata_path(ctx, coll)
            if path:
                avu.rmw_from_data(ctx, path, '%', '%', constants.UUFLATINDEX)
                meta.ingest_metadata_vault(ctx, path)

        # add indexing attribute and update opensearch
        subprocess.call(["imeta", "add", "-C", coll + "/index", "irods::indexing::index", "yoda::metadata", "elasticsearch"])


@rule.make(inputs=[0], outputs=[1])
def rule_vault_disable_indexing(ctx: rule.Context, coll: str) -> str:
    vault_disable_indexing(ctx, coll)
    return "Success"


def vault_disable_indexing(ctx: rule.Context, coll: str) -> None:
    if config.enable_open_search:
        if collection.exists(ctx, coll + "/index"):
            coll = coll + "/index"

        # tricky: remove indexing attribute without updating opensearch
        try:
            msi.mod_avu_metadata(ctx, "-C", coll, "rm", "irods::indexing::index", "yoda::metadata", "elasticsearch")
        except Exception:
            pass


@api.make()
def api_vault_system_metadata(ctx: rule.Context, coll: str) -> api.Result:
    """Return system metadata of a vault collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package

    :returns: Dict system metadata of a vault collection
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

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
        modified_date = parser.parse(row[0])
        modified_date_time = modified_date.strftime('%Y-%m-%d %H:%M:%S%z')
        system_metadata["Modified date"] = "{}".format(modified_date_time)

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


def get_coll_vault_status(ctx: rule.Context, path: str, org_metadata: List | None = None) -> constants.vault_package_state:
    """Get the status of a vault folder."""
    if org_metadata is None:
        org_metadata = folder.get_org_metadata(ctx, path)

    # Don't care about duplicate attr names here.
    org_metadata_dict = dict(org_metadata)
    if constants.IIVAULTSTATUSATTRNAME in org_metadata_dict:
        x = org_metadata_dict[constants.IIVAULTSTATUSATTRNAME]
        try:
            return constants.vault_package_state(x)
        except Exception:
            log.write(ctx, 'Invalid vault folder status <{}>'.format(x))

    return constants.vault_package_state.EMPTY


def get_all_published_versions(ctx: rule.Context, path: str) -> Tuple[str | None, str | None, List]:
    """Get all published versions of a data package."""
    base_doi = get_doi(ctx, path, 'base')
    package_doi = get_doi(ctx, path)
    coll_parent_name = path.rsplit('/', 1)[0]

    org_publ_info, data_packages, grouped_base_dois = get_all_doi_versions(ctx, coll_parent_name)

    count = 0
    all_versions = []

    for data in data_packages:
        if data[2] == package_doi:
            count += 1

    if count == 1:  # Base DOI does not exist as it is first version of the publication
        # Convert the date into two formats for display and tooltip (Jan 1, 1990 and 1990-01-01 00:00:00)
        data_packages = [[x[0], datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime("%b %d, %Y"), x[2],
                          datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime('%Y-%m-%d %H:%M:%S%z'), x[3]] for x in data_packages]

        for item in data_packages:
            if item[2] == package_doi:
                all_versions.append([item[1], item[2], item[3]])
    else:  # Base DOI exists
        # Sort by publication date
        sorted_publ = [sorted(x, key=lambda x: datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f"), reverse=True) for x in grouped_base_dois]

        sorted_publ = [element for innerList in sorted_publ for element in innerList]

        # Convert the date into two formats for display and tooltip (Jan 1, 1990 and 1990-01-01 00:00:00)
        sorted_publ = [[x[0], datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime("%b %d, %Y"), x[2],
                        datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime('%Y-%m-%d %H:%M:%S%z'), x[3]] for x in sorted_publ]

        for item in sorted_publ:
            if item[0] == base_doi:
                all_versions.append([item[1], item[2], item[3]])

    return base_doi, package_doi, all_versions


@api.make()
def api_vault_collection_details(ctx: rule.Context, path: str) -> api.Result:
    """Return details of a vault collection.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to data package

    :returns: Dict with collection details
    """
    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is in vault space.
    space, _, group, subpath = pathutil.info(path)
    if space is not pathutil.Space.VAULT:
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
    meta_embargo_access = {}
    if metadata_path is None:
        return {'member_type': member_type, 'is_datamanager': is_datamanager}
    else:
        # Read the metadata file, might fail if we do not have read access.
        try:
            meta_embargo_access = jsonutil.read(ctx, metadata_path)
            metadata = True
        except Exception:
            metadata = False

        # Retrieve all published versions
        base_doi, package_doi, all_versions = get_all_published_versions(ctx, path)

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
        "research_group_access": research_group_access,
        "all_versions": all_versions,
        "base_doi": base_doi,
        "package_doi": package_doi,
        "embargo_end_date": meta_embargo_access.get("Embargo_End_Date", ""),
        "data_access_restriction": meta_embargo_access.get("Data_Access_Restriction", "")
    }
    result["deaccession"] = {
        "status": vault_deaccession.vault_deaccession_status(ctx, path)
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
def api_vault_get_package_by_reference(ctx: rule.Context, reference: str) -> api.Result:
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
def api_vault_get_landingpage_data(ctx: rule.Context, coll: str) -> api.Result:
    """Retrieve landingpage data of data package.

    Landinpage data consists of metadata and system metadata.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to retrieve landingpage data from

    :returns: API status
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

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
        if str(e).find("-818000") > -1:
            return api.Error('permission_error', 'Action not permitted: no access permission on the metadata file.')
        else:
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
def api_vault_get_publication_terms(ctx: rule.Context) -> api.Result:
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


def change_read_access_group(ctx: rule.Context, coll: str, actor: str, group: str, grant: bool = True) -> Tuple[bool, api.Result]:
    """Grant/revoke research group read access to vault package.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection of data package to grant/remove read rights from
    :param actor: User changing the permissions
    :param group: Group to grant/revoke read access to vault package
    :param grant: Whether to grant or revoke access

    :returns: 2-Tuple of boolean successfully changed, API status if error
    """
    acl_kv = msi.kvpair(ctx, "actor", actor)
    try:
        if grant:
            msi.sudo_obj_acl_set(ctx, "recursive", "read", group, coll, acl_kv)
        else:
            msi.sudo_obj_acl_set(ctx, "recursive", "null", group, coll, acl_kv)
    except Exception:
        policy_error = policies_datamanager.can_datamanager_acl_set(ctx, coll, actor, group, "1", "read")
        if bool(policy_error):
            return False, api.Error('ErrorACLs', 'Could not acquire datamanager access to {}.'.format(coll))
        else:
            return False, api.Error('ErrorACLs', str(policy_error))

    return True, ''


def check_change_read_access_research_group(ctx: rule.Context, coll: str, grant: bool = True) -> Tuple[bool, api.Result]:
    """Initial checks when changing read rights of research group for datapackage in vault.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection of data package to revoke/grant read rights from
    :param grant: Whether to grant or revoke read rights

    :returns: 2-Tuple of boolean whether ok to continue and API status if error
    """
    verb = "grant" if grant else "revoke"

    if not collection.exists(ctx, coll):
        return False, api.Error('nonexistent', 'The given path does not exist')

    coll_parts = coll.split('/')
    if len(coll_parts) != 5:
        return False, api.Error('invalid_collection', 'The datamanager can only {} permissions to vault packages'.format(verb))

    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return False, api.Error('invalid_collection', 'The datamanager can only {} permissions to vault packages'.format(verb))

    return True, ''


def change_read_access_research_group(ctx: rule.Context, coll: str, grant: bool = True) -> api.Result:
    """Grant/revoke read rights of members of research group to a
    datapackage in vault. This operation also includes read only members.

    :param ctx:   Combined type of a callback and rei struct
    :param coll:  Collection of data package to grant/remove read rights from
    :param grant: Whether to grant or revoke access

    :returns: API status
    """
    verb = "granting" if grant else "revoking"
    response, api_error = check_change_read_access_research_group(ctx, coll, True)
    if not response:
        return api_error

    _, _, group, subpath = pathutil.info(coll)

    # Find category
    group_parts = group.split('-')
    if subpath.startswith("deposit-"):
        research_group_name = 'deposit-' + '-'.join(group_parts[1:])
    else:
        research_group_name = 'research-' + '-'.join(group_parts[1:])
    category = groups.group_category(ctx, group)
    read_group_name = 'read-' + '-'.join(group_parts[1:])

    # Is datamanager?
    actor = user.full_name(ctx)
    if groups.user_role(ctx, actor, 'datamanager-' + category) in ['normal', 'manager']:
        # Grant/revoke research group read access to vault package.
        for group_name in (research_group_name, read_group_name):
            response, api_error = change_read_access_group(ctx, coll, actor, group_name, grant)
            if not response:
                return api_error
    else:
        return api.Error('NoDatamanager', 'Actor must be a datamanager for {} access'.format(verb))

    return {'status': 'Success', 'statusInfo': ''}


@api.make()
def api_grant_read_access_research_group(ctx: rule.Context, coll: str) -> api.Result:
    """Grant read rights of research group for datapackage in vault.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to remove read rights from

    :returns: API status
    """
    return change_read_access_research_group(ctx, coll, True)


@api.make()
def api_revoke_read_access_research_group(ctx: rule.Context, coll: str) -> api.Result:
    """Revoke read rights of research group for datapackage in vault.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection of data package to remove read rights from

    :returns: API status
    """
    return change_read_access_research_group(ctx, coll, False)


@rule.make()
def rule_vault_copy_to_vault(ctx: rule.Context) -> None:
    copy_to_vault(ctx, constants.CRONJOB_STATE["PENDING"])
    copy_to_vault(ctx, constants.CRONJOB_STATE["RETRY"])


def copy_to_vault(ctx: rule.Context, state: str) -> None:
    """Collect all folders with a given cronjob state
       and try to copy them to the vault.

    :param ctx:   Combined type of a callback and rei struct
    :param state: One of constants.CRONJOB_STATE
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


def get_copy_to_vault_colls(ctx: rule.Context, cronjob_state: str) -> List:
    iter = list(genquery.Query(ctx,
                ['COLL_NAME'],
                "META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_VALUE = '{}'".format(
                    constants.UUORGMETADATAPREFIX + "cronjob_copy_to_vault",
                    cronjob_state),
                output=genquery.AS_LIST))
    return iter


def copy_folder_to_vault(ctx: rule.Context, coll: str, target: str) -> bool:
    """Copy folder and all its contents to target in vault using irsync.

    The data will reside under folder '/original' within the vault.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Path of a folder in the research space
    :param target: Path of a package in the vault space

    :returns: True for successful copy
    """
    sanity_check_results = get_sanity_checks_results_copy_to_vault_paths(coll, target)
    if len(sanity_check_results) > 0:
        log.write(ctx, "Not copying folder to vault because of sanity check failures: "
                  + str(sanity_check_results))
        return False

    returncode = 0
    irsync_command = get_copy_irsync_command(coll,
                                             f"{target}/original",
                                             config.resource_vault,
                                             config.vault_copy_multithread_enabled)

    try:
        returncode = subprocess.call(irsync_command)
    except Exception as e:
        log.write(ctx, "irsync failure: " + str(e))
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    if returncode != 0:
        log.write(ctx, "irsync failure for coll <{}> and target <{}>".format(coll, target))
        return False

    return True


def set_vault_permissions(ctx: rule.Context, coll: str, target: str) -> bool:
    """Set permissions in the vault as such that data can be copied to the vault."""
    group_name = folder.collection_group_name(ctx, coll)
    if group_name == '':
        log.write(ctx, "set_vault_permissions: Cannot determine which deposit or research group <{}> belongs to".format(coll))
        return False

    parts = group_name.split('-')
    base_name = '-'.join(parts[1:])
    valid_read_groups = [group_name]

    vault_group_name = constants.IIVAULTPREFIX + base_name
    if parts[0] != 'deposit':
        read_group_name = "read-" + base_name
        valid_read_groups.append(read_group_name)

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

        if access_name != "read_object":
            # Grant the research group read-only access to the collection to enable browsing through the vault.
            for name in valid_read_groups:
                try:
                    msi.set_acl(ctx, "default", "admin:read", name, vault_path)
                    log.write(ctx, "Granted " + name + " read access to " + vault_path)
                except msi.Error:
                    log.write(ctx, "Failed to grant " + name + " read access to " + vault_path)

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

    # Grant research group, research group readers read access to vault package.
    for name in valid_read_groups:
        msi.set_acl(ctx, "recursive", "admin:read", name, target)

    return True


def copy_acls_from_parent(ctx: rule.Context, path: str, recursive_flag: str) -> None:
    """
    When inheritance is missing we need to copy ACLs when introducing new data in vault package.

    :param ctx:            Combined type of a ctx and rei struct
    :param path:           Path of object that needs the permissions of parent
    :param recursive_flag: Either "default" for no recursion or "recursive"
    """
    parent = os.path.dirname(path)

    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        access_name = row[0]
        user_id = int(row[1])
        user_name = user.name_from_id(ctx, user_id)

        # iRODS keeps ACLs for deleted users in the iCAT database (https://github.com/irods/irods/issues/7778),
        # so we need to skip ACLs referring to users that no longer exist.
        if user_name == "":
            continue

        if access_name == "own":
            log.write(ctx, "copy_acls_from_parent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "own", user_name, path)
        elif access_name == "read_object":
            log.write(ctx, "copy_acls_from_parent: granting read to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "read", user_name, path)
        elif access_name == "modify_object":
            log.write(ctx, "copy_acls_from_parent: granting write to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "write", user_name, path)


def reader_needs_access(ctx: rule.Context, group_name: str, coll: str) -> bool:
    """Return if research group has access to this group but readers do not"""
    iter = genquery.row_iterator(
        "COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + coll + "'",
        genquery.AS_LIST, ctx
    )
    reader_found = False
    research_found = False

    for row in iter:
        user_id = row[0]
        user_name = user.name_from_id(ctx, user_id)
        # Check if there are *any* readers
        if user_name.startswith('read-'):
            reader_found = True
        elif user_name == group_name:
            research_found = True

    return not reader_found and research_found


def set_reader_vault_permissions(ctx: rule.Context, group_name: str, zone: str, dry_run: bool) -> bool:
    """Given a research group name, give reader group access to
    vault packages if they don't have that access already.

    :param ctx:        Combined type of a callback and rei struct
    :param group_name: Research group name
    :param zone:       Zone
    :param dry_run:    Whether to only print which groups would be changed without changing them

    :return: Boolean whether completed successfully or there were errors.
    """
    parts = group_name.split('-')
    base_name = '-'.join(parts[1:])
    read_group_name = 'read-' + base_name
    vault_group_name = constants.IIVAULTPREFIX + base_name
    vault_path = "/" + zone + "/home/" + vault_group_name
    no_errors = True

    # Do not change the permissions if there aren't any vault packages in this vault.
    if collection.is_empty(ctx, vault_path):
        return True

    if reader_needs_access(ctx, group_name, vault_path):
        # Grant the research group readers read-only access to the collection
        # to enable browsing through the vault.
        try:
            if dry_run:
                log.write(ctx, "Would have granted " + read_group_name + " read access to " + vault_path)
            else:
                msi.set_acl(ctx, "default", "admin:read", read_group_name, vault_path)
                log.write(ctx, "Granted " + read_group_name + " read access to " + vault_path)
        except msi.Error:
            no_errors = False
            log.write(ctx, "Failed to grant " + read_group_name + " read access to " + vault_path)

    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '{}'".format(vault_path),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        target = row[0]
        if reader_needs_access(ctx, group_name, target):
            try:
                if dry_run:
                    log.write(ctx, "Would have granted " + read_group_name + " read access to " + target)
                else:
                    msi.set_acl(ctx, "recursive", "admin:read", read_group_name, target)
                    log.write(ctx, "Granted " + read_group_name + " read access to " + target)
            except Exception:
                no_errors = False
                log.write(ctx, "Failed to set read permissions for <{}> on coll <{}>".format(read_group_name, target))

    return no_errors


@rule.make(inputs=[0, 1], outputs=[2])
def rule_vault_grant_readers_vault_access(ctx: rule.Context, dry_run: str, verbose: str) -> str:
    """Rule for granting reader members of research groups access to vault packages in their
    group if they don't have access already

    :param ctx:     Combined type of a callback and rei struct
    :param dry_run: Whether to only print which groups would be changed without making changes
    :param verbose: Whether to be more verbose

    :return: String status of completed successfully ('0') or there were errors ('1')
    """
    dry_run_mode = (dry_run == '1')
    verbose_mode = (verbose == '1')
    no_errors = True

    log.write(ctx, "grant_readers_vault_access started.")

    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is not rodsadmin")
        return '1'

    if dry_run_mode or verbose_mode:
        modes = []
        if dry_run_mode:
            modes.append("dry run")
        if verbose_mode:
            modes.append("verbose")
        log.write(ctx, "Running grant_readers_vault_access in {} mode.".format((" and ").join(modes)))

    zone = user.zone(ctx)

    # Get the group names
    userIter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_ZONE = '{}' AND USER_GROUP_NAME like 'research-%'".format(zone),
        genquery.AS_LIST,
        ctx)

    for row in userIter:
        name = row[0]
        if verbose:
            log.write(ctx, "{}: checking permissions".format(name))
        if not set_reader_vault_permissions(ctx, name, zone, dry_run_mode):
            no_errors = False

    message = ""
    if no_errors:
        message = "grant_readers_vault_access completed successfully."
    else:
        message = "grant_readers_vault_access completed, with errors."
    log.write(ctx, message)

    return '0' if no_errors else '1'


@rule.make(inputs=[0, 1, 2, 3], outputs=[4, 5])
def rule_vault_process_status_transitions(ctx: rule.Context, coll: str, new_coll_status: str, actor: str, previous_version: str) -> str:
    """Rule interface for processing vault status transition request.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault collection to change status for
    :param new_coll_status:  New vault package status
    :param actor:            Actor of the status change
    :param previous_version: Path to previous version of data package in the vault

    :return: Dict with status and statusinfo.
    """
    vault_process_status_transitions(ctx, coll, new_coll_status, actor, previous_version)

    return 'Success'


def vault_process_status_transitions(ctx: rule.Context, coll: str, new_coll_status: str, actor: str, previous_version: str) -> List:
    """Processing vault status transition request.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault collection to change status for
    :param new_coll_status:  New vault package status
    :param actor:            Actor of the status change
    :param previous_version: Path to previous version of data package in the vault

    :return: List with status and statusinfo
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
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
                    genquery.AS_LIST, ctx
                )

                for row in iter:
                    if row[0] == "":
                        return ['1', 'Landing page is missing']

                # Persistent Identifier DOI.
                iter = genquery.row_iterator(
                    "META_COLL_ATTR_VALUE",
                    "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_versionDOI'" % (coll),
                    genquery.AS_LIST, ctx
                )

                for row in iter:
                    if row[0] == "":
                        return ['1', 'DOI is missing']

    return ['Success', '']


def vault_request_status_transitions(ctx: rule.Context, coll: str, new_vault_status: str, previous_version: str | None = None) -> List:
    """Request vault status transition action.

    :param ctx:              Combined type of a callback and rei struct
    :param coll:             Vault package to be changed of status in publication cycle
    :param new_vault_status: New vault status
    :param previous_version: Path to previous version of data package in the vault

    :return: List with status and statusinfo
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
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
    if previous_version:
        doi = get_doi(ctx, previous_version)
        if doi:
            previous_version_path = previous_version

    # Add vault action request to actor group.
    avu.set_on_coll(ctx, actor_group_path,  constants.UUORGMETADATAPREFIX + 'vault_action_' + coll_id, jsonutil.dump([coll, str(new_vault_status), actor, previous_version_path]))
    # opposite is: jsonutil.parse('["coll","status","actor"]')[0] => coll

    # Add vault action status to actor group.
    avu.set_on_coll(ctx, actor_group_path, constants.UUORGMETADATAPREFIX + 'vault_status_action_' + coll_id, 'PENDING')

    return ['', '']


def set_submitter(ctx: rule.Context, path: str, actor: str) -> None:
    """Set submitter of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_submission_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_submitter(ctx: rule.Context, path: str) -> str:
    """Get submitter of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_submission_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def set_approver(ctx: rule.Context, path: str, actor: str) -> None:
    """Set approver of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_approval_actor"
    avu.set_on_coll(ctx, path, attribute, actor)


def get_approver(ctx: rule.Context, path: str) -> str:
    """Get approver of data package for publication."""
    attribute = constants.UUORGMETADATAPREFIX + "publication_approval_actor"
    org_metadata = dict(folder.get_org_metadata(ctx, path))

    if attribute in org_metadata:
        return org_metadata[attribute]
    else:
        return ""


def get_doi(ctx: rule.Context, path: str, doi: str = 'version') -> str | None:
    """Get the DOI of a data package in the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Vault package to get the DOI of
    :param doi: 'base' or 'version' to retrieve required DOI

    :return: Data package DOI or None
    """
    if doi != 'base':
        doi = 'version'

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'org_publication_{}DOI'".format(path, doi),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_previous_version(ctx: rule.Context, path: str) -> str | None:
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


def get_title(ctx: rule.Context, path: str) -> str:
    """Get the title of a data package in the vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Vault package to get the title of

    :return: Data package title
    """
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = 'Title' AND META_COLL_ATTR_UNITS = '{}_0_s'".format(path, constants.UUUSERMETADATAROOT),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return "(no title)"


def meta_add_new_version(ctx: rule.Context, new_version: str, previous_version: str) -> None:
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


def get_all_doi_versions(ctx: rule.Context, path: str) -> Tuple[List, List, List]:
    """Get the path and DOI of latest versions of published data package in a vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of vault with data packages

    :return: Lists of data packages with DOI
    """

    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, COLL_NAME",
        "COLL_PARENT_NAME = '{}' AND META_COLL_ATTR_NAME IN ('org_publication_versionDOI', 'org_publication_baseDOI', 'org_publication_publicationDate')".format(path),
        genquery.AS_LIST, ctx
    )

    data_packages = []
    org_publ_info = []

    for row in iter:
        org_publ_info.append([row[0], row[1], row[2]])

    # Group by collection name
    coll_names = {x[2] for x in org_publ_info}
    grouped_coll_name = [[y[1] for y in org_publ_info if y[2] == x] + [x] for x in coll_names]

    # If base DOI does not exist, remove from the list and add it in the data package
    number_of_items = list(map(len, grouped_coll_name))
    indices = [i for i, x in enumerate(number_of_items) if x < 4]

    for item in indices:
        data_packages.append([0] + grouped_coll_name[item])

    grouped_coll_name = [grouped_coll_name[i] for i, e in enumerate(grouped_coll_name) if i not in indices]

    # Group by base DOI
    base_dois = {x[0] for x in grouped_coll_name}
    grouped_base_dois = [[y for y in grouped_coll_name if y[0] == x] for x in base_dois]

    return org_publ_info, data_packages, grouped_base_dois


@api.make()
def api_vault_get_published_packages(ctx: rule.Context, path: str) -> Dict:
    """Get the path and DOI of latest versions of published data package in a vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of vault with data packages

    :return: Dict of data packages with DOI
    """
    space, _, _, _ = pathutil.info(path)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    org_publ_info, data_packages, grouped_base_dois = get_all_doi_versions(ctx, path)

    # Sort by publication date
    sorted_publ = [sorted(x, key=lambda x: datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f")) for x in grouped_base_dois]
    latest_publ = [x[-1] for x in sorted_publ]

    # Append to data package
    for items in latest_publ:
        data_packages.append(items)

    # Retrieve title of data packages.
    published_packages = {}
    for item in data_packages:
        published_packages[item[2]] = {"path": item[3], "title": get_title(ctx, item[3])}

    return published_packages


def update_archive(ctx: rule.Context, coll: str, attr: str | None = None) -> None:
    """Potentially update archive after metadata changed.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package
    :param attr: The AVU that was changed, if any
    """
    if config.enable_data_package_archive:
        import vault_archive
        vault_archive.update(ctx, coll, attr)


@rule.make(inputs=[], outputs=[0])
def rule_vault_copy_numthreads(ctx: rule.Context) -> int:
    return get_vault_copy_numthreads(ctx)


def get_current_metadata_schema_data_package(ctx: rule.Context, coll: str) -> str | None:
    (space, _, _, _) = pathutil.info(coll)
    """Get metadata schema of archived data package

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package

    :raises ValueError: if path does not appear to refer to an archived data package
    :returns: Current metadata schema (None if there is no schema definition in the metadata)
    """
    if space is not pathutil.Space.VAULT:
        raise ValueError("Data package path is not in vault space: " + coll)

    metadata_path = meta.get_latest_vault_metadata_path(ctx, coll)
    if metadata_path is None:
        raise ValueError("Data package metadata not found. Path probably does not refer to a data package: " + coll)

    metadata = jsonutil.read(ctx, metadata_path)

    return meta.metadata_get_schema_id(metadata)


def get_latest_action_actor(ctx: rule.Context, path: str) -> str | None:
    """
    Retrieve actor of latest action on vault folder.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path to vault data package

    :returns: Actor of latest action on vault folder (None if there is no latest actor)
    """
    try:
        coll_id = collection.id_from_name(ctx, path)
        action = list(genquery.Query(
                      ctx, "META_COLL_ATTR_VALUE",
                      f"META_COLL_ATTR_NAME = 'org_vault_action_{coll_id}'",
                      order_by="META_COLL_MODIFY_TIME desc",
                      output=genquery.AS_LIST, limit=1, parser=genquery.Parser.GENQUERY2))
        action = json.loads(action[0][0])
        return action[2]
    except Exception:
        return None
