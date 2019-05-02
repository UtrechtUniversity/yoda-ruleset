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

# ------- Global declaration of transformation matrix---------------
# results in a string that is a postfix of two methods:
# 1. execTransformation_
#        executes transformation
# 2. getTransformationText_
#        retrieves the explanation of a transformation in text so an enduser can be informed of what a transformation (in practical terms) entails

transformationMatrix = {}
transformationMatrix['https://yoda.uu.nl/schemas/default-0'] = {'https://yoda.uu.nl/schemas/default-1': 'v1'}


# ----------------------------------- interface functions when calling from irods rules have prefix iiRule

# \brief Transform yoda-metadata.xml from schema x to schema y.
#        Depending on research/vault - different handling.
#
# \param[in] rule_args[0] XML path
# \param[out] rule_args[1] statusPy
# \param[out] rule_args[2] statusInfoPy
#
def iiRuleTransformXml(rule_args, callback, rei):
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


# \brief Check if yoda-metadata.xml transformation from schema x to schema y
#        is possible and retrieve transformation description.
#        Depending on research/vault - different handling.
#
# \param[in] rule_args[0] XML path
# \param[out] rule_args[1] transformation
# \param[out] rule_args[2] transformationText
#
def iiRulePossibleTransformation(rule_args, callback, rei):
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


# General steps within each transformation function
# In reseach:
#   - make copy of yoda-metadata.xml and rename to yoda-metadata[timestamp].xml
#   - write new yoda-metadata.xml
#              including new targetNameSpace etc - so trapping transformation does not occur again
#              This is taken care of within transformation stylesheet
#   - No backup required for yoda-metadata.xml
#   - Do data transformation
#   - Write dataobject to yoda-metadata.xml with timestamp to make it the most recent.

# returns dictionary:
# status
# transformationText - for frontend

def ExecTransformation_v1(callback, xmlPath):
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


# \brief Parse a metadata XML given its path into an ElementTree
#
# \param[in] path Metadata XML path
#
# \return XML parsed as ElementTree
#
def parseXml(callback, path):
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


# \brief Return the metadata schema location based upon the category of a metadata XML
#
# Example:
# in:  /tempZone/home/research-initial/yoda-metadata.xml
# out: 'https://yoda.uu.nl/schemas/default-0'
#
# \param[in] rule_args[0] XML path
# \param[out] rule_args[1] Metadata schema location
#
def iiRuleGetLocation(rule_args, callback, rei):
    rule_args[1] = getSchemaLocation(callback, rule_args[0])


# \brief Return the metadata schema space based upon the category of a metadata XML
#
# Example:
# in:  /tempZone/home/research-initial/yoda-metadata.xml
# out: 'research.xsd'
#
# \param[in] rule_args[0] XML path
# \param[out] rule_args[1] Metadata schema space
#
def iiRuleGetSpace(rule_args, callback, rei):
    pathParts = rule_args[0].split('/')
    rods_zone = pathParts[1]
    group_name = pathParts[3]
    rule_args[1] = getSchemaSpace(callback, group_name)


# \brief Return the location of schema of a metadata XML
#
# Example:
# in:  /tempZone/home/research-initial/yoda-metadata.xml
# out: 'https://yoda.uu.nl/schemas/default-0'
#
# \param[in] rule_args[0] XML path
# \param[out] rule_args[1] Metadata schema location
#
def iiRuleGetMetadataXMLSchema(rule_args, callback, rei):
    rule_args[1] = getMetadataXMLSchema(callback, rule_args[0])


# \brief Determine category based upon rods zone and name of the group
#
# \param[in] rods_zone
# \param[in] group_name
#
# \return schema space
#
def getCategory(callback, rods_zone, group_name):
    category = '-1'
    schemaCategory = 'default'

    # Find out category based on current group_name.
    ret_val = callback.msiMakeGenQuery(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + group_name + "' AND  META_USER_ATTR_NAME like 'category'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        # Check each data object in batch.
        for row in range(0, result.rowCnt):
            attrValue = result.sqlResult[1].row(row)
            category = attrValue

    if category != '-1':
        # Test whether found category actually has a collection with XSD's.
        # If not, fall back to default schema collection. Otherwise use category schema collection
        # /tempZone/yoda/schemas/default
        # - metadata.xsd
        # - vault.xsd
        xsdCollectionName = '/' + rods_zone + '/yoda/schemas/' + category
        ret_val = callback.msiMakeGenQuery(
            "COLL_NAME",
            "DATA_NAME like '%%.xsd' AND COLL_NAME = '" + xsdCollectionName + "'",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        if result.rowCnt != 0:
            schemaCategory = category    # As collection is present, the schemaCategory can be assigned the category

    return schemaCategory


# \brief Based upon the category of the current yoda-metadata.xml file,
#        return the active metadata schema involved.
#
# \param[in] xmlPath
#
# \return Schema location
#
def getSchemaLocation(callback, xmlPath):
    # Retrieve current metadata schemas.
    pathParts = xmlPath.split('/')
    rods_zone = pathParts[1]
    group_name = pathParts[3]

    schemaCategory = getCategory(callback, rods_zone, group_name)

    jsonSchemaPath = '/' + rods_zone + '/yoda/schemas/' + schemaCategory + '/metadata.json'
    jsonSchema = parseJson(callback, jsonSchemaPath)
    schema, jsonFile = os.path.split(jsonSchema["$id"])

    return schema


# \brief Based upon the group name of the current yoda-metadata.xml file,
#     return the (research or vault) XSD schema involved.
#
# \param[in] group_name
#
# \return schema space
#
def getSchemaSpace(callback, group_name):
    if 'research-' in group_name:
        space = 'research'
    else:
        space = 'vault'

    return space + '.xsd'



# \brief getLatestVaultMetadataXml
#
# \param[in] vaultPackage
#
# \return metadataXmlPath
#
def getLatestVaultMetadataXml(callback, vaultPackage):
    ret_val = callback.msiMakeGenQuery(
        "DATA_NAME, DATA_SIZE",
        "COLL_NAME = '" + vaultPackage + "' AND DATA_NAME like 'yoda-metadata[%].xml'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())

    # Loop through all XMLs.
    dataName = ""
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            data_name = result.sqlResult[0].row(row)
            data_size = int(result.sqlResult[1].row(row))

            if dataName == "" or (dataName < data_name and len(dataName) <= len(data_name)):
                dataName = data_name

        # Continue with this query.
        if result.continueInx == 0:
            break

        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

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


# \brief getDataObjSize
#
# \param[in] coll_name Data object collection name
# \param[in] data_name Data object name
#
# \return Data object size
#
def getDataObjSize(callback, coll_name, data_name):
    ret_val = callback.msiMakeGenQuery(
        "DATA_SIZE",
        "COLL_NAME = '%s' AND DATA_NAME = '%s'" % (coll_name, data_name),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    data_size = 0
    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            data_size = result.sqlResult[0].row(row)

    return data_size


# \brief getUserNameFromUserId
#
# \param[in] user_id User id
#
# \return User name
#
def getUserNameFromUserId(callback, user_id):
    ret_val = callback.msiMakeGenQuery(
        "USER_NAME",
        "USER_ID = '%s'" % (str(user_id)),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    user_name = ''
    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            user_name = result.sqlResult[0].row(row)

    return user_name


# \brief When inheritance is missing we need to copy ACL's when introducing new data in vault package.
#
# \param[in] path               Path of object that needs the permissions of parent
# \param[in] recursive_flag     either "default" for no recursion or "recursive"
#
def copyACLsFromParent(callback, path, recursive_flag):
    parent = os.path.dirname(path)

    ret_val = callback.msiMakeGenQuery(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            access_name = result.sqlResult[0].row(row)
            user_id = int(result.sqlResult[1].row(row))
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


# \brief Parse XML into an ElementTree.
#
# \param[in] path Path of metadata XML to parse
#
# \return Parsed XML as ElementTree.
#
def parseMetadataXml(callback, path):
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
    return ET.fromstring(xmlText)


# \brief Parse JSON file into JSON dict.
#
# \param[in] path Path of JSON file to parse
#
# \return Parsed JSON as dict.
#
def parseJson(callback, path):
    # Retrieve JSON size.
    coll_name, data_name = os.path.split(path)
    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open JSON file.
    ret_val = callback.msiDataObjOpen('objPath=' + path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read JSON file.
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close JSON file.
    callback.msiDataObjClose(fileHandle, 0)

    # Parse JSON.
    read_buf = ret_val['arguments'][2]
    jsonText = ''.join(read_buf.buf)
    return json.loads(jsonText)


# \brief Check metadata XML for possible schema updates.
#
# \param[in] rods_zone  Zone name
# \param[in] coll_name  Collection name of metadata XML
# \param[in] group_name Group name of metadata XML
# \param[in] data_name  Data name of metadata XML
##
def checkMetadataXmlForSchemaUpdates(callback, rods_zone, coll_name, group_name, data_name):
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

# \brief Loop through all collections with yoda-metadata.xml data objects.
#        Check metadata XML for schema updates.
#
# \param[in] rods_zone Zone name
# \param[in] coll_id   First collection id of batch
# \param[in] batch     Batch size, <= 256
# \param[in] pause     Pause between checks (float)
#
# \return Collection id to continue with in next batch.
#
def checkMetadataXmlForSchemaUpdatesBatch(callback, rods_zone, coll_id, batch, pause):
    import time

    # Find all research and vault collections, ordered by COLL_ID.
    ret_val = callback.msiMakeGenQuery(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/%%' AND DATA_NAME like 'yoda-metadata%%xml' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        # Check each collection in batch.
        for row in range(min(batch, result.rowCnt)):
            coll_id = int(result.sqlResult[0].row(row))
            coll_name = result.sqlResult[1].row(row)
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

# \brief Check metadata XML for schema identifier.
#
# \param[in] rods_zone  Zone name
# \param[in] coll_name  Collection name of metadata XML
# \param[in] group_name Group name of metadata XML
# \param[in] data_name  Data name of metadata XML
#
def checkMetadataXmlForSchemaIdentifier(callback, rods_zone, coll_name, group_name, data_name):
    xml_file = coll_name + "/" + data_name

    try:
        root = parseMetadataXml(callback, coll_name + "/" + data_name)

        # Check if no identifiers are present, for vault and research space.
        if not root.attrib:
            callback.writeLine("stdout", "Missing schema identifier: %s" % (xml_file))
     except:
         callback.writeLine("stdout", "Unparsable metadata file: %s" % (xml_file))


# \brief Check metadata XML for schema identifiers.
#
def iiCheckMetadataXmlForSchemaIdentifier(rule_args, callback, rei):
    import session_vars
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    callback.writeString("stdout", "[METADATA] Start check for schema identifiers.\n")

    # Find all research and vault collections, ordered by COLL_ID.
    ret_val = callback.msiMakeGenQuery(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/%%' AND DATA_NAME like 'yoda-metadata%%xml'" % (rods_zone),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        # Check each collection in batch.
        for row in range(0, result.rowCnt):
            coll_id = int(result.sqlResult[0].row(row))
            coll_name = result.sqlResult[1].row(row)
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

# \brief Check metadata XML for schema updates.
#
# \param[in] coll_id  first COLL_ID to check
# \param[in] batch    batch size, <= 256
# \param[in] pause    pause between checks (float)
# \param[in] delay    delay between batches in seconds
#
def iiCheckMetadataXmlForSchemaUpdates(rule_args, callback, rei):
    import session_vars

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
