# \file      iiSchemaUpdates.py
# \brief     Functions for handling schema updates within any yoda-metadata.xml.
# \author    Lazlo Westerhof
# \author    Felix Croes
# \author    Harm de Raaff
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import os
from collections import namedtuple
from enum import Enum
import hashlib
import base64
import json
import irods_types
import lxml.etree as etree
import xml.etree.ElementTree as ET
import time

import genquery
import session_vars


# ------- Global declaration of transformation matrix---------------
# results in a string that is a postfix of two methods:
# 1. execTransformation_
#        executes transformation
# 2. getTransformationText_
#        retrieves the explanation of a transformation in text so an enduser can be informed of what a transformation (in practical terms) entails
transformationMatrix = {}
transformationMatrix['https://yoda.uu.nl/schemas/default-0'] = {'https://yoda.uu.nl/schemas/default-1': 'v1'}


# ----------------------------------- interface functions when calling from irods rules have prefix iiRule

def iiRuleTransformXml(rule_args, callback, rei):
    """Transform yoda-metadata.xml from schema x to schema y.
       Depending on research/vault - different handling.

       Arguments:
       rule_args[0] -- XML path

       Return:
       rule_args[1] -- statusPy
       rule_args[2] -- statusInfoPy
    """
    xmlPath = rule_args[0] + "/yoda-metadata.xml"

    status = 'Unknown'
    statusInfo = ''

    try:
        # Retrieve current and future  metadata schemas.
        versionTo = getSchemaLocation(callback, xmlPath)
        versionFrom = getMetadataXMLSchema(callback, xmlPath)

        transformationMethod = 'ExecTransformation_' + transformationMatrix[versionFrom][versionTo]
        result = globals()[transformationMethod](callback, xmlPath)
        status = result['status']
    except KeyError:
        # No transformation present to convert yoda-metadata.xml
        status = 'ERROR'
        statusInfo = 'No transformation known for bringing yoda-metadata.xml up to date'

    rule_args[1] = status
    rule_args[2] = statusInfo


def iiRulePossibleTransformation(rule_args, callback, rei):
    """Check if yoda-metadata.xml transformation from schema x to schema y
       is possible and retrieve transformation description.
       Depending on research/vault - different handling.

       Arguments:
       rule_args[0] -- XML path

       Return:
       rule_args[1] -- transformation
       rule_args[2] -- transformationText
    """
    xmlPath = rule_args[0]

    transformation = 'false'
    transformationText = ''

    try:
        # Retrieve current and future  metadata schemas.
        versionTo = getSchemaLocation(callback, xmlPath)
        versionFrom = getMetadataXMLSchema(callback, xmlPath)

        transformationMethod = 'GetTransformationText_' + transformationMatrix[versionFrom][versionTo]
        transformationText = globals()[transformationMethod](callback, xmlPath)
        transformation = 'true'
    except KeyError:
        pass

    rule_args[1] = transformation
    rule_args[2] = transformationText

# ------------------ end of interface functions -----------------------------


def ExecTransformation_v1(callback, xmlPath):
    """General steps within each transformation function.

       In reseach:
       - make copy of yoda-metadata.xml and rename to yoda-metadata[timestamp].xml
       - write new yoda-metadata.xml
         including new targetNameSpace etc - so trapping transformation does not occur again
         This is taken care of within transformation stylesheet
       - No backup required for yoda-metadata.xml
       - Do data transformation
       - Write dataobject to yoda-metadata.xml with timestamp to make it the most recent.

       Return:
       dict -- Status and transformation text for frontend.

    """
    coll_name, data_name = os.path.split(xmlPath)
    pathParts = xmlPath.split('/')
    rods_zone = pathParts[1]
    groupName = pathParts[3]

    transformationBasePath = '/' + rods_zone + '/yoda/transformations/default-1'

    # Select correct transformation file.
    if "research" in groupName:
        xslFilename = 'default-0-research.xsl'
    elif "vault" in groupName:
        xslFilename = 'default-0-vault.xsl'

    xslroot = parseXml(callback, transformationBasePath + '/' + xslFilename)

    # Retrieve Yoda metadata XML.
    xmlYodaMeta = parseXml(callback, xmlPath)

    transform = etree.XSLT(xslroot)
    transformationResult = transform(xmlYodaMeta, encoding='utf8')
    transformedXml = etree.tostring(transformationResult, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    # Write transformed xml to yoda-metadata.xml
    if "research" in groupName:
        # First save original yoda-metadata.xml
        copiedYodaXml = coll_name + '/transformation-backup' + '[' + str(int(time.time())) + '].xml'
        callback.writeString("serverLog", copiedYodaXml)
        callback.msiDataObjCopy(xmlPath, copiedYodaXml, '', 0)

        # Prepare writing dataobject
        ofFlags = 'forceFlag='  # File already exists, so must be overwritten.
        xml_file = coll_name + "/" + 'yoda-metadata.xml'
        ret_val = callback.msiDataObjCreate(xml_file, ofFlags, 0)

        # Now write actual new contents
        fileHandle = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileHandle, transformedXml, 0)
        callback.msiDataObjClose(fileHandle, 0)
        callback.writeString("serverLog", "[TRANSFORMED METADATA SCHEMA] %s" % (xml_file))
    elif "vault" in groupName:
        # Prepare writing transformed metadata schema to the vault.
        ofFlags = ''
        xml_file = coll_name + '/yoda-metadata[' + str(int(time.time())) + '].xml'
        ret_val = callback.msiDataObjCreate(xml_file, ofFlags, 0)

        # Now write actual new contents
        fileHandle = ret_val['arguments'][2]
        callback.msiDataObjWrite(fileHandle, transformedXml, 0)
        callback.msiDataObjClose(fileHandle, 0)
        copyACLsFromParent(callback, xml_file, "default")

        # Add item to provenance log.
        callback.iiAddActionLogRecord("system", coll_name, "updated metadata schema")

        callback.writeString("serverLog", "[TRANSFORMED METADATA SCHEMA] %s" % (xml_file))

    result = {}
    result['status'] = 'Success'
    return result


def GetTransformationText_v1(callback, xmlPath):
    htmlFilename = 'default-0.html'
    pathParts = xmlPath.split('/')
    rods_zone = pathParts[1]

    transformationBasePath = '/' + rods_zone + '/yoda/transformations/default-1'

    # Collect the transformation explanation text for the enduser.
    data_size = getDataObjSize(callback, transformationBasePath, htmlFilename)
    path = transformationBasePath + '/' + htmlFilename

    # Open transformation information file.
    ret_val = callback.msiDataObjOpen('objPath=' + path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read data.
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close transformation information file.
    callback.msiDataObjClose(fileHandle, 0)

    read_buf = ret_val['arguments'][2]
    transformationText = ''.join(read_buf.buf)

    return transformationText


def parseXml(callback, path):
    """Parse a metadata XML given its path into an ElementTree.

       Arguments:
       path -- Path of metadata XML

       Return:
       XML parsed as ElementTree
    """
    # Retrieve XML size.
    coll_name, data_name = os.path.split(path)
    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open metadata XML.
    ret_val = callback.msiDataObjOpen('objPath=' + path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read metadata XML.
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close metadata XML.
    callback.msiDataObjClose(fileHandle, 0)

    # Parse XML.
    read_buf = ret_val['arguments'][2]
    xmlText = ''.join(read_buf.buf)
    return etree.fromstring(xmlText)


def iiRuleGetLocation(rule_args, callback, rei):
    """Return the metadata schema location based upon the category of a metadata XML.

       Example:
       in:  /tempZone/home/research-initial/yoda-metadata.xml
       out: 'https://yoda.uu.nl/schemas/default-0'

       Arguments:
       rule_args[0] -- Path of metadata XML

       Return:
       rule_args[1] -- Metadata schema location
    """
    rule_args[1] = getSchemaLocation(callback, rule_args[0])


def iiRuleGetSpace(rule_args, callback, rei):
    """Return the metadata schema space based upon the category of a metadata XML.

       Example:
       in:  /tempZone/home/research-initial/yoda-metadata.xml
       out: 'research.xsd'

       Arguments:
       rule_args[0] -- Path of metadata XML

       Return:
       rule_args[1] -- Metadata schema space
    """
    pathParts = rule_args[0].split('/')
    rods_zone = pathParts[1]
    group_name = pathParts[3]
    rule_args[1] = getSchemaSpace(callback, group_name)


def iiRuleGetMetadataXMLSchema(rule_args, callback, rei):
    """Return the location of schema of a metadata XML.

       Example:
       in:  /tempZone/home/research-initial/yoda-metadata.xml
       out: 'https://yoda.uu.nl/schemas/default-0'

       Arguments:
       rule_args[0] -- Path of metadata XML

       Return:
       rule_args[1] -- Metadata schema location
    """
    rule_args[1] = getMetadataXMLSchema(callback, rule_args[0])


def getCategory(callback, rods_zone, group_name):
    """Determine category based upon rods zone and name of the group.

       Arguments:
       rods_zone  -- Rods zone name
       group_name -- Group name

       Return:
       string -- Category
    """
    category = '-1'
    schemaCategory = 'default'

    # Find out category based on current group_name.
    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + group_name + "' AND  META_USER_ATTR_NAME like 'category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        category = row[1]

    if category != '-1':
        # Test whether found category actually has a metadata JSON.
        # If not, fall back to default schema collection.
        # /tempZone/yoda/schemas/default/metadata.json
        schemaCollectionName = '/' + rods_zone + '/yoda/schemas/' + category

        iter = genquery.row_iterator(
            "COLL_NAME",
            "DATA_NAME like 'metadata.json' AND COLL_NAME = '" + schemaCollectionName + "'",
            genquery.AS_LIST, callback
        )

        for row in iter:
            schemaCategory = category    # As collection is present, the schemaCategory can be assigned the category

    return schemaCategory


def getSchemaPath(callback, metadata_path):
    """Get the iRODS path to a schema file from the path to a yoda metadata file.

       Arguments:
       metadata_path -- Path of metadata XML

       Return:
       Schema path (e.g. /tempZone/yoda/schemas/.../metadata.json
    """
    # Retrieve current metadata schemas.
    path_parts = metadata_path.split('/')
    rods_zone  = path_parts[1]
    group_name = path_parts[3]

    if group_name.startswith("vault-"):
        group_name = group_name.replace("vault-", "research-", 1)

    category = getCategory(callback, rods_zone, group_name)

    return '/' + rods_zone + '/yoda/schemas/' + category + '/metadata.json'


def getSchema(callback, metadata_path):
    """Get a schema object from the path to a yoda metadata file.

       Arguments:
       metadata_path -- Path of metadata XML

       Return:
       Schema object (parsed from JSON)
    """
    return read_json_object(callback, getSchemaPath(callback, metadata_path))


def getSchemaUrl(callback, metadata_path):
    """Get a schema URL from the path to a yoda metadata file.

       Arguments:
       metadata_path -- Path of metadata XML

       Return:
       string -- Schema URL (e.g. https://yoda.uu.nl/schemas/...)
    """
    schema = getSchema(callback, metadata_path)
    url, jsonFile = os.path.split(schema["$id"])

    return url


def getSchemaLocation(callback, xmlPath):
    """Based upon the category of the current yoda-metadata.xml file,
       return the active metadata schema involved.

       Arguments:
       xmlPath -- Path of metadata XML

       Return:
       string -- Schema location
    """
    return getSchemaUrl(callback, xmlPath)


def getSchemaSpace(callback, group_name):
    """Based upon the group name of the current yoda-metadata.xml file,
       return the (research or vault) XSD schema involved.

       Arguments:
       group_name -- Name of the group

       Return:
       string -- Schema space
    """
    if 'research-' in group_name:
        space = 'research'
    else:
        space = 'vault'

    return space + '.xsd'


def getLatestVaultMetadataXml(callback, vaultPackage):
    """Get the latest vault metadata XML.

       Arguments:
       vaultPackage -- Vault package collection

       Return:
       string -- Metdata XML path
    """
    dataName = ""

    iter = genquery.row_iterator(
        "DATA_NAME, DATA_SIZE",
        "COLL_NAME = '" + vaultPackage + "' AND DATA_NAME like 'yoda-metadata[%].xml'",
        genquery.AS_LIST, callback
    )

    # Loop through all XMLs.
    for row in iter:
            data_name = row[0]
            data_size = int(row[1])

            if dataName == "" or (dataName < data_name and len(dataName) <= len(data_name)):
                dataName = data_name

    return dataName


def getMetadataXMLSchema(callback, xmlPath):
    schema = ""
    try:
        root = parseMetadataXml(callback, xmlPath)
    except:
        return schema

    return getMetadataSchemaFromTree(callback, root)


def getMetadataSchemaFromTree(callback, root):
    schema = ""

    # Check if root attributes are present.
    if root.attrib:
        key = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        schemaLocation = root.attrib[key]

        schema = schemaLocation.split()[0]

    return schema


def getDataObjSize(callback, coll_name, data_name):
    """Get data object size.

       Arguments:
       coll_name -- Data object collection name
       data_name -- Data object name

       Return:
       integer -- Data object size
    """
    iter = genquery.row_iterator(
        "DATA_SIZE, order_desc(DATA_MODIFY_TIME)",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % (coll_name, data_name),
        genquery.AS_LIST, callback
    )

    for row in iter:
        return int(row[0])
    else:
        return -1


def getUserNameFromUserId(callback, user_id):
    """Retrieve username from user ID.

       Arguments:
       user_id -- User id

       Return:
       string -- User name
    """
    user_name = ""

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_ID = '%s'" % (str(user_id)),
        genquery.AS_LIST, callback
    )

    for row in iter:
        user_name = row[0]

    return user_name


def copyACLsFromParent(callback, path, recursive_flag):
    """When inheritance is missing we need to copy ACL's when introducing new data in vault package.

       Arguments:
       path           -- Path of object that needs the permissions of parent
       recursive_flag -- Either "default" for no recursion or "recursive"
    """
    parent = os.path.dirname(path)

    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        access_name = row[0]
        user_id = int(row[1])

        user_name = getUserNameFromUserId(callback, user_id)

        if access_name == "own":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "own", user_name, path)
        elif access_name == "read object":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "read", user_name, path)
        elif access_name == "modify object":
            callback.writeString("serverLog", "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            callback.msiSetACL(recursive_flag, "write", user_name, path)


def parseMetadataXml(callback, path):
    """Parse XML into an ElementTree.

       Arguments:
       path -- Path of metadata XML to parse

       Return:
       Parsed XML as ElementTree.
    """
    return ET.fromstring(read_data_object(callback, path))


def parseJson(callback, path):
    """Parse JSON file into JSON dict.

       Arguments:
       path -- Path of JSON file to parse

       Return:
       Parsed JSON as dict.
    """
    return json.loads(read_data_object(callback, path))


def checkMetadataXmlForSchemaUpdates(callback, rods_zone, coll_name, group_name, data_name):
    """Check metadata XML for possible schema updates.

    Arguments:
    rods_zone  -- Zone name
    coll_name  -- Collection name of metadata XML
    group_name -- Group name of metadata XML
    data_name  -- Data name of metadata XML
    """
    root = parseMetadataXml(callback, coll_name + "/" + data_name)

    # Retrieve active schema location to be added.
    schemaLocation = getSchemaLocation(callback, coll_name + "/" + data_name)

    # Check if no attributes are present, for vault and research space.
    # If not, add xmlns:xsi and xsi:schemaLocation attributes.
    if not root.attrib:
        schemaSpace = getSchemaSpace(callback, group_name)

        if schemaLocation != '-1' or schemaSpace != '-1':
            root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            root.set('xmlns', schemaLocation)
            root.set('xsi:schemaLocation', schemaLocation + ' ' + schemaSpace)
            newXmlString = ET.tostring(root, encoding='UTF-8')

            if "research" in group_name:
                ofFlags = 'forceFlag='  # File already exists, so must be overwritten.
                xml_file = coll_name + "/" + data_name
                ret_val = callback.msiDataObjCreate(xml_file, ofFlags, 0)
            elif "vault" in group_name:
                ofFlags = ''
                xml_file = coll_name + '/yoda-metadata[' + str(int(time.time())) + '].xml'
                ret_val = callback.msiDataObjCreate(xml_file, ofFlags, 0)
                copyACLsFromParent(callback, xml_file, "default")

                # Add item to provenance log.
                callback.iiAddActionLogRecord("system", coll_name, "updated metadata schema")

            fileHandle = ret_val['arguments'][2]
            callback.msiDataObjWrite(fileHandle, newXmlString, 0)
            callback.msiDataObjClose(fileHandle, 0)
            callback.writeString("serverLog", "[ADDED SCHEMA TO METADATA] %s" % (xml_file))
    # Only transform metadata schemas in the vault space.
    # Transformations in research space are initiated by the researcher.
    elif "vault" in group_name:
        # Retrieve current active system schema and schema from metadata.
        versionTo = schemaLocation
        versionFrom = getMetadataSchemaFromTree(callback, root)

        # Only try transformation if schemas don't match.
        if versionTo != versionFrom:
            try:
                xmlPath = coll_name + "/" + data_name
                transformationMethod = 'ExecTransformation_' + transformationMatrix[versionFrom][versionTo]
                result = globals()[transformationMethod](callback, xmlPath)
            except:
                callback.writeString("serverLog", "[TRANSFORMING METADATA FAILED] %s" % (xml_file))
    else:
        callback.writeString("serverLog", "[METADATA NOT TRANSFORMED] %s" % (xml_file))


def checkMetadataXmlForSchemaUpdatesBatch(callback, rods_zone, coll_id, batch, pause):
    """Loop through all collections with yoda-metadata.xml data objects
       and check metadata XML for schema updates.

       Arguments:
       rods_zone -- Zone name
       coll_id   -- First collection id of batch
       batch     -- Batch size, <= 256
       pause     -- Pause between checks (float)

       Return:
       coll_id -- Collection id to continue with in next batch.
   """
    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/%%' AND DATA_NAME like 'yoda-metadata%%xml' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        genquery.AS_LIST, callback
    )

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        pathParts = coll_name.split('/')

        try:
            group_name = pathParts[3]
            if 'research-' in group_name:
                checkMetadataXmlForSchemaUpdates(callback, rods_zone, coll_name, group_name, "yoda-metadata.xml")
            elif 'vault-' in group_name:
                # Get vault package path.
                vault_package = '/'.join(pathParts[:5])
                data_name = getLatestVaultMetadataXml(callback, vault_package)
                if data_name != "":
                    checkMetadataXmlForSchemaUpdates(callback, rods_zone, vault_package, group_name, data_name)
        except:
            pass

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id = coll_id + 1
    else:
        # All done.
        coll_id = 0
        callback.writeString("serverLog", "[METADATA] Finished updating metadata.")

    return coll_id


def checkMetadataXmlForSchemaIdentifier(callback, rods_zone, coll_name, group_name, data_name):
    """Check metadata XML for schema identifier.

       Arguments:
       rods_zone  -- Zone name
       coll_name  -- Collection name of metadata XML
       group_name -- Group name of metadata XML
       data_name  -- Data name of metadata XML
    """
    xml_file = coll_name + "/" + data_name

    try:
        root = parseMetadataXml(callback, coll_name + "/" + data_name)

        # Check if no identifiers are present, for vault and research space.
        if not root.attrib:
            callback.writeLine("stdout", "Missing schema identifier: %s" % (xml_file))
    except:
        callback.writeLine("stdout", "Unparsable metadata file: %s" % (xml_file))


def iiCheckMetadataXmlForSchemaIdentifier(rule_args, callback, rei):
    """Check metadata XML for schema identifiers."""
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    callback.writeString("stdout", "[METADATA] Start check for schema identifiers.\n")

    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/%%' AND DATA_NAME like 'yoda-metadata%%xml'" % (rods_zone),
        genquery.AS_LIST, callback
    )

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        pathParts = coll_name.split('/')

        group_name = pathParts[3]
        if 'research-' in group_name:
            checkMetadataXmlForSchemaIdentifier(callback, rods_zone, coll_name, group_name, "yoda-metadata.xml")
        elif 'vault-' in group_name:
            # Get vault package path.
            vault_package = '/'.join(pathParts[:5])
            data_name = getLatestVaultMetadataXml(callback, vault_package)
            if data_name != "":
                checkMetadataXmlForSchemaIdentifier(callback, rods_zone, vault_package, group_name, data_name)
            else:
                callback.writeLine("stdout", "Missing metadata file: %s" % (vault_package))

    callback.writeString("stdout", "[METADATA] Finished check for schema identifiers.\n")


def iiCheckMetadataXmlForSchemaUpdates(rule_args, callback, rei):
    """Check metadata XML for schema updates.

       Arguments:
       coll_id -- first COLL_ID to check
       batch   -- batch size, <= 256
       pause   -- pause between checks (float)
       delay   -- delay between batches in seconds
    """
    coll_id = int(rule_args[0])
    batch = int(rule_args[1])
    pause = float(rule_args[2])
    delay = int(rule_args[3])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one batch of metadata schemas.
    coll_id = checkMetadataXmlForSchemaUpdatesBatch(callback, rods_zone, coll_id, batch, pause)

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "iiCheckMetadataXmlForSchemaUpdates('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")
