# \file      iiVault.py
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import os

import genquery
import session_vars


# \brief Retrieve lists of preservable file formats on the system.
#
# \return Lists of preservable file formats
#
def getPreservableFormatsLists(callback, rei):
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
        json = parseJson(callback, coll_name + "/" + data_name)

        # Add to list of preservable file formats.
        preservableLists[filename] = json

    return {'lists': preservableLists}


# \brief Retrieve all unpreservable files in a folder.
#
# \param[in] folder Path of folder to check.
# \param[in] list   Name of preservable file format list.
#
# \return List of unpreservable files.
#
def getUnpreservableFiles(callback, rei, folder, list):
    zoneName = ""
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Retrieve JSON list of preservable file formats.
    json = parseJson(callback, "/" + rods_zone + "/yoda/file_formats/" + list + ".json")
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


# \brief Write preservable file formats lists to stdout.
#
def iiGetPreservableFormatsListsJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getPreservableFormatsLists(callback, rei)))


# \brief Write unpreservable files in folder to stdout.
#
# \param[in] rule_args[0] Path of folder to check.
# \param[in] rule_args[1] Name of preservable file format list.
#
def iiGetUnpreservableFilesJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getUnpreservableFiles(callback, rei, rule_args[0], rule_args[1])))


# \brief Copy the original metadata xml into the root of the package.
#
# \param[in] rule_args[0] Path of a new package in the vault.
#
def iiCopyOriginalMetadataToVault(rule_args, callback, rei):
    vaultPackage = rule_args[0]
    originalMetadataXml = vaultPackage + "/original/" + IIMETADATAXMLNAME

    # Parse original metadata.
    tree = parseXml(callback, originalMetadataXml)
    xmlString = ('<?xml version="1.0" encoding="UTF-8"?>' + '\n' +
                 etree.tostring(tree, pretty_print=True, xml_declaration=False, encoding="UTF-8"))

    # Retrieve active schema location and space to be added.
    schemaLocation = getSchemaLocation(callback, vaultPackage)

    # Set 'xsi:schemaLocation' for the vault space.
    researchSchema = "xsi:schemaLocation=\"" + schemaLocation + " " + IIRESEARCHXSDNAME + "\""
    vaultSchema = "xsi:schemaLocation=\"" + schemaLocation + " " + IIVAULTXSDNAME + "\""
    xmlString = xmlString.decode('utf-8')
    newXmlString = xmlString.replace(researchSchema, vaultSchema, 1)

    # Write new metadata XML.
    ofFlags = ''
    xml_file = vaultPackage + '/yoda-metadata[' + str(int(time.time())) + '].xml'
    ret_val = callback.msiDataObjCreate(xml_file, ofFlags, 0)
    fileHandle = ret_val['arguments'][2]
    callback.msiDataObjWrite(fileHandle, newXmlString, 0)
    callback.msiDataObjClose(fileHandle, 0)

    # Checksum new metadata XML.
    callback.msiDataObjChksum(xml_file, "verifyChksum=", 0)


# \brief Get the provenance log as JSON.
#
# \param[in] folder Path of a folder in research or vault space.
#
# \return Provenance log as JSON.
#
def getProvenanceLog(callback, folder):
    provenance_log = []

    # Retrieve all provenance logs on a folder.
    iter = genquery.row_iterator(
        "order(META_COLL_ATTR_VALUE)",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_action_log'" % (folder),
        genquery.AS_LIST, callback
    )

    for row in iter:
        log_item = json.loads(row[0])
        provenance_log.append(log_item)

    return provenance_log


# \brief Writes the provenance log as a text file into the root of the vault package.
#
# \param[in] rule_args[0] Path of a package in the vault.
#
def iiWriteProvenanceLogToVault(rule_args, callback, rei):
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
