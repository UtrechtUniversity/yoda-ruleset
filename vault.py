# -*- coding: utf-8 -*-
"""Functions to copy packages to the vault and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time
import itertools

import genquery
import session_vars

from util import *

__all__ = ['rule_uu_vault_preservable_formats_lists',
           'rule_uu_vault_unpreservable_files',
           'rule_uu_vault_copy_original_metadata_to_vault',
           'rule_uu_vault_write_provenance_log',
           'rule_uu_vault_system_metadata']


def getPreservableFormatsLists(callback, rei):
    """Retrieve lists of preservable file formats on the system.

    :returns: dict -- Lists of preservable file formats
    """
    zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Retrieve all preservable file formats lists on the system.

    files = [x for x in collection.data_objects(callback, '/{}/yoda/file_formats'.format(zone))
             if x.endswith('.json')]

    # Return dict of list filename (without extension) -> JSON contents
    return {'lists': { os.path.splitext(pathutil.chop(x)[1])[0]:
                           jsonutil.read(callback, x) for x in files }}


def getUnpreservableFiles(callback, path, list_name):
    """Retrieve lists of unpreservable file formats in a collection.

    :param path: Path of folder to check.
    :param list_name: Name of preservable file format list

    :returns: dict -- Lists of unpreservable file formats
    """
    zone = pathutil.info(path)[1]

    # Retrieve JSON list of preservable file formats.
    list_data = jsonutil.read(callback, '/{}/yoda/file_formats/{}.json'.format(zone, list_name))
    preservable_formats = set(list_data['formats'])

    # Get basenames of all data objects within this collection.
    data_names = itertools.imap(lambda x: pathutil.chop(x)[1],
                                collection.data_objects(callback, path, recursive=True))

    # If JSON is considered unpreservable, ignore yoda-metadata.json.
    data_names = itertools.ifilter(lambda x: x != unicode(constants.IIJSONMETADATA), data_names)

    # Data names -> lowercase extensions, without the dot.
    exts = set(itertools.imap(lambda x: os.path.splitext(x)[1][1:].lower(), data_names))

    # Return any ext that is not in the preservable list.
    return {'formats': list(exts - preservable_formats)}


def rule_uu_vault_preservable_formats_lists(rule_args, callback, rei):
    """Write preservable file formats lists to stdout."""
    callback.writeString("stdout", jsonutil.dump(getPreservableFormatsLists(callback, rei)))


def rule_uu_vault_unpreservable_files(rule_args, callback, rei):
    """Write unpreservable files in folder to stdout.

    :param rule_args[0]: Path of folder to check.
    :param rule_args[1]: Name of preservable file format list.
    """
    callback.writeString("stdout", jsonutil.dump(getUnpreservableFiles(callback, rule_args[0], rule_args[1])))


def rule_uu_vault_copy_original_metadata_to_vault(rule_args, callback, rei):
    """Copy the original metadata JSON into the root of the package.

    :param rule_args[0]: Path of a new package in the vault.
    """
    vault_package = rule_args[0]
    original_metadata = vault_package + "/original/" + constants.IIJSONMETADATA

    # Copy original metadata JSON.
    copied_metadata = vault_package + '/yoda-metadata[' + str(int(time.time())) + '].json'
    callback.msiDataObjCopy(original_metadata, copied_metadata, 'verifyChksum=', 0)


def getProvenanceLog(callback, folder):
    """Get the provenance log of a folder.

    :param folder: Path of a folder in research or vault space.

    :returns dict: Provenance log.
    """
    provenance_log = []

    # Retrieve all provenance logs on a folder.
    iter = genquery.row_iterator(
        "order(META_COLL_ATTR_VALUE)",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_action_log'" % (folder),
        genquery.AS_LIST, callback
    )

    for row in iter:
        log_item = jsonutil.parse(row[0])
        provenance_log.append(log_item)

    return provenance_log


def rule_uu_vault_write_provenance_log(rule_args, callback, rei):
    """Writes the provenance log as a text file into the root of the vault package.

    :param rule_args[0]: Path of a package in the vault.
    """
    # Retrieve provenance.
    provenenanceString = ""
    provenanceLog = getProvenanceLog(callback, rule_args[0])

    for item in provenanceLog:
        dateTime = time.strftime('%Y/%m/%d %H:%M:%S',
                                 time.localtime(int(item[0])))
        action = item[1].capitalize()
        actor = item[2]
        provenenanceString += dateTime + " - " + action + " - " + actor + "\n"

    # Write provenance log.
    ofFlags = 'forceFlag='  # File already exists, so must be overwritten.
    provenanceFile = rule_args[0] + "/Provenance.txt"
    ret_val = callback.msiDataObjCreate(provenanceFile, ofFlags, 0)

    fileHandle = ret_val['arguments'][2]
    callback.msiDataObjWrite(fileHandle, provenenanceString, 0)
    callback.msiDataObjClose(fileHandle, 0)

    # Checksum provenance file.
    callback.msiDataObjChksum(provenanceFile, "verifyChksum=", 0)


def vault_collection_metadata(callback, coll):
    """Returns collection statistics as JSON."""

    import math

    def convert_size(size_bytes):
        if size_bytes == 0:
            return "0B"

        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
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

rule_uu_vault_system_metadata = rule.make(inputs=[0], outputs=[1],
                                       transform=jsonutil.dump, handler=rule.Output.STDOUT) \
                                      (vault_collection_metadata)
