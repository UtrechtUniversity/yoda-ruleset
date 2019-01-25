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
import irods_types
import xml.etree.ElementTree as ET
import time

# ----------------------------------- interface functions when calling from irods rules have prefix iiRule
# Return the location of schema location based upon the category within the path
# /in rule_args[0] path
# /out rule_args[1] public xsd location

# Example:
# in:  /tempZone/home/research-initial/yoda-metadata.xml
# out: 'https://utrechtuniversity.github.io/yoda-schemas/default'

def iiRuleGetLocation(rule_args, callback, rei):
    pathParts = rule_args[0].split('/')
    rods_zone = pathParts[1]
    group_name = pathParts[3]
    rule_args[1] = getSchemaLocation(callback, rods_zone, group_name)

# Return the location of schema space based upon the category within the path
# /in rule_args[0] path
# /out rule_args[1] public xsd location

# Example:
# in:  /tempZone/home/research-initial/yoda-metadata.xml
# out: 'research.xsd'

def iiRuleGetSpace(rule_args, callback, rei):
    pathParts = rule_args[0].split('/')
    rods_zone = pathParts[1]
    group_name = pathParts[3]
    rule_args[1] = getSchemaSpace(callback, group_name)

#------------------------------------- end of interface part

# Based upon the category of the current yoda-metadata.xml file, return the XSD schema involved.
# Schema location depends on the category the yoda-metadata.xml belongs to.
# If the specific category XSD does not exist, fall back to /default/research.xsd or /default/vault.xsd.
def getSchemaLocation(callback, rods_zone, group_name):
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

    return 'https://utrechtuniversity.github.io/yoda-schemas/' + schemaCategory


# Based upon the group name of the current yoda-metadata.xml file, return the (research or vault) XSD schema involved.
def getSchemaSpace(callback, group_name):
    space = '-1'

    if 'research-' in group_name:
        space = 'research'
    elif 'vault-' in group_name:
        space = 'vault'
    else:
        return '-1'

    return space + '.xsd'


# \brief getLatestVaultMetadataXml
#
# \param[in] vaultPackage
#
# \return metadataXmlPath
#
def getLatestVaultMetadataXml(callback, vaultPackage):
    dataNameQuery = "yoda-metadata[%].xml"
    ret_val = callback.msiMakeGenQuery(
        "DATA_NAME, DATA_SIZE",
        "COLL_NAME = '" + vaultPackage + "' AND DATA_NAME like '" + dataNameQuery + "'",
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


# \brief Check metadata XML for possible schema updates.
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


# \brief Check metadata XML for possible schema updates.
#
# \param[in] rods_zone  Zone name
# \param[in] coll_name  Collection name of metadata XML
# \param[in] group_name Group name of metadata XML
# \param[in] data_name  Data name of metadata XML
##
def checkMetadataXmlForSchemaUpdates(callback, rods_zone, coll_name, group_name, data_name):
    root = parseMetadataXml(callback, coll_name + "/" + data_name)

    # Check if no attributes are present.
    # If not, add xmlns:xsi and xsi:schemaLocation attributes.
    if not root.attrib:
        # Retrieve Schema location to be added.
        schemaLocation = getSchemaLocation(callback, rods_zone, group_name)
        schemaSpace = getSchemaSpace(callback, group_name)

        if schemaLocation != '-1' or schemaSpace != '-1':
            root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            root.set('xsi:noNamespaceSchemaLocation', schemaLocation + ' ' + schemaSpace)
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

            fileHandle = ret_val['arguments'][2]
            callback.msiDataObjWrite(fileHandle, newXmlString, 0)
            callback.msiDataObjClose(fileHandle, 0)
            callback.writeString("serverLog", "[UPDATE METADATA SCHEMA] %s" % (xml_file))


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
                    # Parent collections should not be 'original'. Those files must remain untouched.
                    if pathParts[-1] != 'original':
                        data_name = getLatestVaultMetadataXml(callback, coll_name)
                        checkMetadataXmlForSchemaUpdates(callback, rods_zone, coll_name, group_name, data_name)
            except:
                pass

            # Sleep briefly between checks.
            time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id = coll_id + 1
    else:
        # All done.
        coll_id = 0

    return coll_id


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
            "checkMetadataXmlForSchemaUpdatesBatch('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")
