# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time
import itertools

import session_vars
import provenance
import meta_form
import meta

from util import *


__all__ = ['api_uu_vault_preservable_formats_lists',
           'api_uu_vault_unpreservable_files',
           'rule_uu_vault_copy_original_metadata_to_vault',
           'rule_uu_vault_write_provenance_log',
           'api_uu_vault_system_metadata',
           'api_uu_vault_collection_details']


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


def rule_uu_vault_write_provenance_log(rule_args, callback, rei):
    """Writes the provenance log as a text file into the root of the vault package.

    :param rule_args[0]: Path of a package in the vault.
    """
    # Retrieve provenance.
    provenenance_txt = ""
    provenance_log = provenance.get_provenance_log(callback, rule_args[0])

    for item in provenance_log:
        date_time = time.strftime('%Y/%m/%d %H:%M:%S',
                                 time.localtime(int(item[0])))
        action = item[1].capitalize()
        actor = item[2]
        provenenance_txt += date_time + " - " + action + " - " + actor + "\n"

    # Write provenance log.
    ofFlags = 'forceFlag='  # File already exists, so must be overwritten.
    provenance_file = rule_args[0] + "/Provenance.txt"
    ret_val = callback.msiDataObjCreate(provenance_file, ofFlags, 0)

    file_handle = ret_val['arguments'][2]
    callback.msiDataObjWrite(file_handle, provenenance_txt, 0)
    callback.msiDataObjClose(file_handle, 0)

    # Checksum provenance file.
    callback.msiDataObjChksum(provenance_file, "verifyChksum=", 0)


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
        metadata= True

    # Retrieve vault folder status.
    status = meta_form.get_coll_vault_status(ctx, path)

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
