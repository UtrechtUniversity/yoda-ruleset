# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import itertools
import os
import time

import folder
import meta
import meta_form
import session_vars
from util import *

__all__ = ['api_uu_vault_submit',
           'api_uu_vault_approve',
           'api_uu_vault_cancel',
           'api_uu_vault_depublish',
           'api_uu_vault_republish',
           'api_uu_vault_preservable_formats_lists',
           'api_uu_vault_unpreservable_files',
           'rule_uu_vault_copy_original_metadata_to_vault',
           'rule_uu_vault_write_license',
           'api_uu_vault_system_metadata',
           'api_uu_vault_collection_details',
           'api_uu_vault_copy_to_research']


def submit(ctx, coll):
    res = ctx.iiVaultSubmit(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])
    return res['arguments'][1]


def approve(ctx, coll):
    res = ctx.iiVaultApprove(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])


def cancel(ctx, coll):
    res = ctx.iiVaultCancel(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])


def depublish(ctx, coll):
    res = ctx.iiVaultDepublish(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])


def republish(ctx, coll):
    res = ctx.iiVaultRepublish(coll, '', '')
    if res['arguments'][1] != 'Success':
        return api.Error(*res['arguments'][1:])


def vault_copy_to_research(ctx, coll_origin, coll_target):
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

    callback.delayExec(
        "<PLUSET>%ds</PLUSET>" % delay,
        "iiCopyFolderToResearch('%s', '%s')" % (coll_origin, coll_target),
        "")

    # TODO: response nog veranderen
    return {"status": "ok",
            "target": coll_target,
            "origin": coll_origin}


api_uu_vault_submit           = api.make()(submit)
api_uu_vault_approve          = api.make()(approve)
api_uu_vault_cancel           = api.make()(cancel)
api_uu_vault_depublish        = api.make()(depublish)
api_uu_vault_republish        = api.make()(republish)
api_uu_vault_copy_to_research = api.make()(vault_copy_to_research)


def preservable_formats_lists(ctx):
    """Retrieve lists of preservable file formats on the system.

    :returns: dict -- Lists of preservable file formats {name => [ext...]}
    """
    zone = user.zone(ctx)

    # Retrieve all preservable file formats lists on the system.

    files = [x for x in collection.data_objects(ctx, '/{}/yoda/file_formats'.format(zone))
             if x.endswith('.json')]

    # Return dict of list filename (without extension) -> JSON contents
    return {os.path.splitext(pathutil.chop(x)[1])[0]:
            jsonutil.read(ctx, x) for x in files}


def unpreservable_files(ctx, path, list_name):
    """Retrieve the set of unpreservable file formats in a collection.

    :param path: Path of folder to check.
    :param list_name: Name of preservable file format list

    :returns: Set of unpreservable file formats
    """
    zone = pathutil.info(path)[1]

    # Retrieve JSON list of preservable file formats.
    list_data = jsonutil.read(ctx, '/{}/yoda/file_formats/{}.json'.format(zone, list_name))
    preservable_formats = set(list_data['formats'])

    # Get basenames of all data objects within this collection.
    data_names = itertools.imap(lambda x: pathutil.chop(x)[1],
                                collection.data_objects(ctx, path, recursive=True))

    # If JSON is considered unpreservable, ignore yoda-metadata.json.
    data_names = itertools.ifilter(lambda x: x != constants.IIJSONMETADATA, data_names)

    # Data names -> lowercase extensions, without the dot.
    exts  = set(list(itertools.imap(lambda x: os.path.splitext(x)[1][1:].lower(), data_names)))
    exts -= set([''])

    # Return any ext that is not in the preservable list.
    return exts - preservable_formats


@api.make()
def api_uu_vault_preservable_formats_lists(ctx):
    """Write preservable file formats lists to stdout."""
    return preservable_formats_lists(ctx)


@api.make()
def api_uu_vault_unpreservable_files(ctx, coll, list_name):
    """Write unpreservable files in folder to stdout.

    :param coll:      Path of folder to check.
    :param list_name: Name of preservable file format list.
    """
    return list(unpreservable_files(ctx, coll, list_name))


def rule_uu_vault_copy_original_metadata_to_vault(rule_args, callback, rei):
    """Copy the original metadata JSON into the root of the package.

    :param rule_args[0]: Path of a new package in the vault.
    """
    vault_package = rule_args[0]
    original_metadata = vault_package + "/original/" + constants.IIJSONMETADATA

    # Copy original metadata JSON.
    copied_metadata = vault_package + '/yoda-metadata[' + str(int(time.time())) + '].json'
    callback.msiDataObjCopy(original_metadata, copied_metadata, 'verifyChksum=', 0)


def rule_uu_vault_write_license(rule_args, callback, rei):
    """Writes the license as a text file into the root of the vault package.

    :param rule_args[0]: Path of a package in the vault.
    """

    vault_pkg_coll = rule_args[0]
    zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Retrieve license.
    license = ""
    license_key = "License"
    license_unit = "{}_%".format(constants.UUUSERMETADATAROOT)

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}' AND META_COLL_ATTR_UNITS LIKE '{}'".format(vault_pkg_coll, license_key, license_unit),
        genquery.AS_LIST, callback)

    for row in iter:
        license = row[0]

    if license == "":
        # No license set in user metadata.
        log.write(callback, "rule_uu_vault_write_license: No license found in user metadata <{}>".format(vault_pkg_coll))
    elif license == "Custom":
        # Custom license set in user metadata, no License.txt should exist in package.
        license_file = vault_pkg_coll + "/License.txt"
        if data_object.exists(callback, license_file):
            data_object.remove(callback, license_file)
    else:
        # License set in user metadata, a License.txt should exist in package.
        # Check if license text exists.
        license_txt = "/{}{}/{}.txt".format(zone, constants.IILICENSECOLLECTION, license)
        if data_object.exists(callback, license_txt):
            # Copy license file.
            license_file = vault_pkg_coll + "/License.txt"
            data_object.copy(callback, license_txt, license_file)

            # Fix ACLs.
            try:
                callback.iiCopyACLsFromParent(license_file, 'default')
            except Exception as e:
                log.write(callback, "rule_uu_vault_write_license: Failed to set vault permissions on <{}>".format(license_file))
        else:
            log.write(callback, "rule_uu_vault_write_license: License text not available for <{}>".format(license))

        # Check if license URI exists.
        license_uri_file = "/{}{}/{}.uri".format(zone, constants.IILICENSECOLLECTION, license)
        if data_object.exists(callback, license_uri_file):
            # Retrieve license URI.
            license_uri = data_object.read(callback, license_uri_file)
            license_uri = license_uri.strip()
            license_uri = license_uri.strip('\"')

            # Set license URI.
            avu.set_on_coll(callback, vault_pkg_coll, "{}{}".format(constants.UUORGMETADATAPREFIX, "license_uri"), license_uri)
        else:
            log.write(callback, "rule_uu_vault_write_license: License URI not available for <{}>".format(license))


@api.make()
def api_uu_vault_system_metadata(callback, coll):
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
    return constants.vault_package_state.UNPUBLISHED


@api.make()
def api_uu_vault_collection_details(ctx, path):
    """Returns details of a vault collection."""

    if not collection.exists(ctx, path):
        return api.Error('nonexistent', 'The given path does not exist')

    # Check if collection is a research group.
    space, _, group, _ = pathutil.info(path)
    if space != pathutil.Space.VAULT:
        return {}

    basename = pathutil.chop(path)[1]

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

    # Check if research group has access.
    research_group_access = True

    # Check if research space is accessible.
    research_path = ""
    research_name = group.replace("vault-", "research-", 1)
    if collection.exists(ctx, pathutil.chop(path)[0] + "/" + research_name):
        research_path = research_name

    return {"basename": basename,
            "status": status,
            "metadata": metadata,
            "has_datamanager": has_datamanager,
            "is_datamanager": is_datamanager,
            "vault_action_pending": vault_action_pending,
            "research_group_access": research_group_access,
            "research_path": research_path}
