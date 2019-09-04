# \file      iiVault.py
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import os

import genquery
import session_vars


def getPreservableFormatsLists(callback, rei):
    """Retrieve lists of preservable file formats on the system.

       Return:
       dict -- Lists of preservable file formats
    """
    preservableLists = {}
    zoneName = ""
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Retrieve all preservable file formats lists on the system.
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME = '/{}/yoda/file_formats' AND DATA_NAME like '%%.json'".format(rods_zone),
        genquery.AS_LIST, callback
    )

    for row in iter:
        data_name = row[0]
        coll_name = row[1]

        # Retrieve filename and name of list.
        filename, file_extension = os.path.splitext(data_name)
        json = read_json_object(callback, coll_name + "/" + data_name)

        # Add to list of preservable file formats.
        preservableLists[filename] = json

    return {'lists': preservableLists}


def getUnpreservableFiles(callback, rei, folder, list):
    """Retrieve lists of preservable file formats on the system.

       Arguments:
       folder -- Path of folder to check.
       list   -- Name of preservable file format list.

       Return:
       dict -- Lists of preservable file formats
    """
    zoneName = ""
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Retrieve JSON list of preservable file formats.
    json = read_json_object(callback, "/" + rods_zone + "/yoda/file_formats/" + list + ".json")
    preservableFormats = json['formats']
    unpreservableFormats = []

    # Retrieve all files in collection.
    iter = genquery.row_iterator(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME like '%s%%'" % (folder),
        genquery.AS_LIST, callback
    )

    for row in iter:
        filename, file_extension = os.path.splitext(row[0])

        # Convert to lowercase and remove dot.
        file_extension = (file_extension.lower())[1:]

        # Check if extention is in preservable format list.
        if (file_extension not in preservableFormats):
            unpreservableFormats.append(file_extension)

    # Remove duplicate file formats.
    output = []
    for x in unpreservableFormats:
        if x not in output:
            output.append(x)

    return {'formats': output}


def iiGetPreservableFormatsListsJson(rule_args, callback, rei):
    """Write preservable file formats lists to stdout."""
    callback.writeString("stdout", json.dumps(getPreservableFormatsLists(callback, rei)))


def iiGetUnpreservableFilesJson(rule_args, callback, rei):
    """Write unpreservable files in folder to stdout.

       Arguments:
       rule_args[0] -- Path of folder to check.
       rule_args[1] -- Name of preservable file format list.
    """
    callback.writeString("stdout", json.dumps(getUnpreservableFiles(callback, rei, rule_args[0], rule_args[1])))


def iiCopyOriginalMetadataToVault(rule_args, callback, rei):
    """Copy the original metadata JSON into the root of the package.

       Arguments:
       rule_args[0] -- Path of a new package in the vault.
    """
    vault_package = rule_args[0]
    original_metadata = vault_package + "/original/" + IIJSONMETADATA

    # Copy original metadata JSON.
    copied_metadata = vault_package + '/yoda-metadata[' + str(int(time.time())) + '].json'
    callback.msiDataObjCopy(original_metadata, copied_metadata, 'verifyChksum=', 0)


def getProvenanceLog(callback, folder):
    """Get the provenance log of a folder.

       Arguments:
       folder -- Path of a folder in research or vault space.

       Return:
       dict -- Provenance log.
    """
    provenance_log = []

    # Retrieve all provenance logs on a folder.
    iter = genquery.row_iterator(
        "order(META_COLL_ATTR_VALUE)",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_action_log'" % (folder),
        genquery.AS_LIST, callback
    )

    for row in iter:
        log_item = parse_json(row[0])
        provenance_log.append(log_item)

    return provenance_log


def iiWriteProvenanceLogToVault(rule_args, callback, rei):
    """Writes the provenance log as a text file into the root of the vault package.

       Arguments:
       rule_args[0] -- Path of a package in the vault.
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
