# -*- coding: utf-8 -*-
"""Functions for transforming vault XML to JSON."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import xmltodict
from collections import OrderedDict

from util import *

__all__ = ['rule_uu_vault_xml_to_json_check_vault_metadata_xml_for_transformation_to_json']


def getMetadataXmlAsDict(callback, path):
    """Get the content of a yoda-metadata.xml file and return parsed into a dict."""
    return xmltodict.parse(data_object.read(callback, path))


def getMetadaJsonDict(callback, yoda_json_path):
    """Get Json Schema of category and return as (ordered!) dict."""
    return jsonutil.read(callback, yoda_json_path)


def getActiveJsonSchemaAsDict(callback, rods_zone, category):  # irods-ruleset-uu function in uuResources.py
    """Read yoda-metadata.json from vault and return as (ordered!) dict."""
    json_schema_path = '/' + rods_zone + '/yoda/schemas/' + category + '/metadata.json'
    return jsonutil.read(callback, json_schema_path)


def transformYodaXmlDataToJson(callback, dictSchema, xmlData):
    """Turn yoda-metadata.xml into JSON

    :param dictSchema: JSON schema that yoda-metadata.xml must be transformed to
    :param xmlData: Dict with all data in yoda-metadata.xml

    :returns: dict -- JSON formatted string holding content of yoda-metadata.xml
    """
    jsonDict = {}

    for elementName in dictSchema['properties']:
        elementInfo = dictSchema['properties'][elementName]

        try:  # CHECK IF DATA IS PRESENT
            data = xmlData['metadata'][elementName]

            if isinstance(data, list):  # Multiple data entries for given elemenent
                totalElementList = []
                newData = {}
                for dataItem in data:  # MULTIPLE ENTRIES IN DATA
                    if isinstance(dataItem, dict):  # hier de structuur uitvissen
                        fieldIsMultiple = True  # kan als zeker worden aangenomen nu! Hoeft niet te worden getest omdat de data al multiple wordt aangeleverd
                        newData = {}

                        try:
                            # Als er sprake is van ['items'] +> dan is vanaf het hoogste niveau een structuur bekend van subproperties // compounds
                            if elementInfo['items']['yoda:structure'] == 'subproperties':
                                # hier volgt een structuur. Zal altijd een subproperty struct zijn vanaf dit niveau
                                counter = 0
                                for subElement, subElementInfo in elementInfo['items']['properties'].items():
                                    if counter == 0:  # MAIN PART of subproperty structure  ! in itself always a single value
                                        # Added these extra variables for clearer name purposes as there is a distinction between main/sub elements
                                        mainElement = subElement
                                        mainElementVal = dataItem[subElement]
                                        newData[mainElement] = mainElementVal  # # MAINPART of subproperty structure IS ALWAYS SINGULAR!
                                    else:  # SUB PART of subproperty structure - corresponding data is beneath <Properties> tag within XML
                                        subPropertyElement = subElement

                                        # I this a single or multiple subproperty element??
                                        subIsMultiple = False
                                        try:
                                            subIsMultiple = (subElementInfo['type'] == 'array')
                                        except KeyError:
                                            pass

                                        try:
                                            # Als type = array zit alles een niveau dieper met 'items' er nog tussen
                                            if subIsMultiple:
                                                compoundInfo = subElementInfo['items']
                                            else:
                                                compoundInfo = subElementInfo

                                            if compoundInfo['yoda:structure'] == 'compound':  # Dit kan ook nog weer multiple of single zijn!!
                                                # als multiple is, moet sowieso data uitmonden in list
                                                dataList = []
                                                # For easy stepping through data, if single entry (=dict), convert it to a list with 1 entry
                                                if (isinstance(dataItem['Properties'][subPropertyElement], dict)):
                                                    # Create a list from a dict
                                                    dataList = [dataItem['Properties'][subPropertyElement]]
                                                else:
                                                    # Already a list
                                                    dataList = dataItem['Properties'][subPropertyElement]

                                                listCompoundData = []  # required to compile multiple compound entries
                                                for dataItem2 in dataList:
                                                    compoundDict = {}
                                                    for compoundElement in compoundInfo['properties']:
                                                        compoundDict[compoundElement] = dataItem2[compoundElement]  # ['Properties'][subPropertyElement][compoundElement]

                                                    listCompoundData.append(compoundDict)

                                                # Alle data is doorlopen voor dit sompound element.
                                                if subIsMultiple:
                                                    newData[subElement] = listCompoundData  # LIST of dicts oontaining compound values
                                                else:
                                                    newData[subElement] = listCompoundData[0]  # compoundDict # Single dict

                                        except KeyError as e:
                                            if subIsMultiple and not isinstance(dataItem['Properties'][subPropertyElement], list):
                                                newData[subElement] = [dataItem['Properties'][subPropertyElement]]
                                            else:
                                                newData[subElement] = dataItem['Properties'][subPropertyElement]
                                            pass

                                    counter = counter + 1

                                totalElementList.append(newData)
                        except KeyError:
                            pass
                    else:  # SINGLE ENTRY e.g. Discipline
                        totalElementList.append(dataItem)

                jsonDict[elementName] = totalElementList

            elif isinstance(data, dict):  # Single structure
                fieldIsMultiple = (elementInfo['type'] == 'array')
                newData = {}

                try:
                    # Als er sprake is van ['items'] +> dan is vanaf het hoogste niveau een structuur bekend van subproperties // compounds
                    if elementInfo['items']['yoda:structure'] == 'subproperties':
                        counter = 0

                        for subElement, subElementInfo in elementInfo['items']['properties'].items():  # keys(): #items()):

                            if counter == 0:  # MAIN PART of subproperty structure  ! in itself always a single value
                                # Added these extra variables for clearer name purposes as there is a distinction between main/sub elements
                                mainElement = subElement
                                mainElementVal = data[subElement]
                                newData[mainElement] = mainElementVal  # # MAINPART of subproperty structure IS ALWAYS SINGULAR!
                            else:  # SUB PART of subproperty structure - corresponding data is beneath <Properties> tag within XML
                                subPropertyElement = subElement

                                # I this a single or multiple subproperty element??
                                subIsMultiple = False
                                try:
                                    subIsMultiple = (subElementInfo['type'] == 'array')
                                except KeyError:
                                    pass

                                try:
                                    # Als type = array zit alles een niveau dieper met 'items' er nog tussen
                                    if subIsMultiple:
                                        compoundInfo = subElementInfo['items']
                                    else:
                                        compoundInfo = subElementInfo

                                    if compoundInfo['yoda:structure'] == 'compound':  # Dit kan ook nog weer multiple of single zijn!!
                                        # als multiple is, moet sowieso data uitmonden in list
                                        dataList = []
                                        # For easy stepping through data, if single entry (=dict), convert it to a list with 1 entry
                                        if (isinstance(data['Properties'][subPropertyElement], dict)):
                                            # Create a list from a dict
                                            dataList = [data['Properties'][subPropertyElement]]
                                        else:
                                            # Already a list
                                            dataList = data['Properties'][subPropertyElement]

                                        listCompoundData = []  # required to compile multiple compound entries
                                        for dataItem in dataList:
                                            compoundDict = {}
                                            for compoundElement in compoundInfo['properties']:
                                                compoundDict[compoundElement] = dataItem[compoundElement]  # ['Properties'][subPropertyElement][compoundElement]

                                            listCompoundData.append(compoundDict)

                                        # Alle data is doorlopen voor dit sompound element.
                                        if subIsMultiple:
                                            newData[subElement] = listCompoundData  # LIST of dicts oontaining compound values
                                        else:
                                            newData[subElement] = listCompoundData[0]  # compoundDict # Single dict

                                except KeyError as e:
                                    if subIsMultiple and not isinstance(data['Properties'][subPropertyElement], list):
                                        newData[subElement] = [data['Properties'][subPropertyElement]]
                                    else:
                                        newData[subElement] = data['Properties'][subPropertyElement]
                                    pass

                            counter = counter + 1

                    # Add to element
                    if fieldIsMultiple:
                        jsonDict[elementName] = [newData]
                    else:
                        jsonDict[elementName] = newData

                except KeyError as e:
                    pass

                try:
                    if elementInfo['yoda:structure'] == 'compound':  # Compound handling on highest level, i.e. not as part of subproperty structure
                        # Build a list of compound elements / values
                        # print(elementInfo)
                        # print(elementInfo['type'])
                        compoundList = []  # ALS cmopound type = 'array' is ipv 'object', dienen alle compoundDicts opgevangen te worden in deze list. Hier betreft het enkelvoudige data maar mogelijk toch een list toevoegen
                        secondList = {}
                        for compoundElementName in elementInfo['properties']:
                            try:
                                compoundList.append({compoundElementName: data[compoundElementName]})
                                secondList[compoundElementName] = data[compoundElementName]
                            except KeyError:
                                print('error')
                                pass

                        if (len(compoundList)):
                            # Dit kunnen meerdere compounds  zijn, dan moet het een list worden.
                            #
                            jsonDict[elementName] = secondList  # compoundList   #@TODO uitwerken!!
                except KeyError:
                    continue

            else:  # Single value
                try:
                    if elementName == 'Retention_Period':  # Can be hardcoded, as this script is for one situation solely
                        jsonDict[elementName] = int(data)
                    else:
                        jsonDict[elementName] = data
                except KeyError:
                    pass

        except KeyError:  # No data present for this element
            pass

    try:
        jsonDict['System'] = {
            'Last_Modified_Date': xmlData['metadata']['System']['Last_Modified_Date'],
            'Persistent_Identifier_Datapackage': {
                'Identifier_Scheme': 'DOI',
                'Identifier': xmlData['metadata']['System']['Persistent_Identifier_Datapackage']['Identifier']
            },
            'Publication_Date': xmlData['metadata']['System']['Publication_Date'],
            'Open_access_Link': xmlData['metadata']['System']['Open_Access_Link'],
            'License_URI': xmlData['metadata']['System']['License_URI']
        }
    except KeyError:  # only published area contains system metadata, not data in the vault
        pass

    return jsonutil.dump(jsonDict)


def transformVaultMetadataXmlToJson(callback, rods_zone, vault_collection, group_name, xml_data_name):
    """Convert current yoda-metadata.xml to yoda-metadata.json.

    :param rods_zone: Zone name
    :param vault_collection: Collection name of metadata XML
    :param group_name: Group name of metadata XML
    :param xml_data_name: Data name of metadata XML that requires transformation
    """

    # This function simply transforms given data_name to a Json data object.
    # No further intelligence required further.
    # Perhaps handling within vault??

    ofFlags = ''
    json_file = vault_collection + '/yoda-metadata[' + str(int(time.time())) + '].json'

    ret_val = callback.msiDataObjCreate(json_file, ofFlags, 0)

    copyACLsFromParent(callback, json_file, "default")

    xmlDataDict = getMetadataXmlAsDict(callback, vault_collection + "/" + xml_data_name)

    # take category incuding version from declared namespace in xml
    category_version = xmlDataDict['metadata']['@xmlns'].split('/')[-1]
    log.write(callback, category_version)

    dictSchema = getActiveJsonSchemaAsDict(callback, rods_zone, category_version)

    # for test in xmlDataDict:
    #    for test1 in xmlDataDict[test]:
    #        #print(test + ' -' + test1)
    #        if isinstance(xmlDataDict[test][test1], dict):
    #            for test2 in xmlDataDict[test][test1]:
    #                log.write(callback, test + ' -' + test1 + ' -- ' + test2 )

    newJsonDataString = transformYodaXmlDataToJson(callback, dictSchema, xmlDataDict)

    fileHandle = ret_val['arguments'][2]
    callback.msiDataObjWrite(fileHandle, newJsonDataString, 0)
    callback.msiDataObjClose(fileHandle, 0)

    # Add item to provenance log.
    callback.iiAddActionLogRecord("system", vault_collection, "Transformed yoda-metadata.xml to yoda-metadata.json")

    log.write(callback, "[ADDED METADATA.JSON AFTER TRANSFORMATION] %s" % (json_file))


def iiCheckVaultMetadataXmlForTransformationToJsonBatch(callback, rods_zone, coll_id, batch, pause):
    """Loop through all collections with yoda-metadata.xml data objects.
       If NO yoda-metadata.json is found in that collection,
       the corresponding yoda-metadata.xml must be converted to json as an extra file - yoda-metadata.json

    :param rods_zone: Zone name
    :param coll_id: First collection id of batch
    :param batch: Batch size, <= 256
    :param pause: Pause between checks (float)

    :returns: integer -- Collection id to continue with in next batch.
                         If collection_id=0, no more collections are found containing yoda-metadata.xml
    """
    import genquery
    import time

    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_NAME like 'yoda-metadata[%%].xml' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        genquery.AS_LIST, callback
    )

    # A collection can hold multiple metadata-schemas and that will result in an equal amount of equal coll_id's
    prev_coll_id = -1  # A collection can hold multiple metadata-schemas and that will result in an equal amount of equal coll_id's
    # Check each collection in batch.
    for row in iter:

        coll_id = int(row[0])

        if coll_id == prev_coll_id:  # coll_id should be processed only once!
            continue

        prev_coll_id = coll_id

        coll_name = row[1]
        pathParts = coll_name.split('/')

        try:
            group_name = pathParts[3]
            vault_collection = '/'.join(pathParts[:5])

            # First make sure that no metadata json file exists already in the vault collection .
            # If so, no transformation is required.
            # As it is unknown what the exact name is of the JSON file, use wildcards:

            # There is no need to specifically test for the samen name.
            # The area that is looked into, cannot be accessed by a YoDa user. I.e. the user can not have placed any json files.
            # If a json file is present, this can only have been added by this batch

            jsonFound = False
            iter2 = genquery.row_iterator(
                "ORDER(COLL_ID), COLL_NAME",
                "DATA_NAME like 'yoda-metadata%%.json' AND COLL_ID = '%d'" % (coll_id),
                genquery.AS_LIST, callback)

            for row2 in iter2:
                jsonFound = True
                continue

            if not jsonFound:
                date_name = ''
                metadataXmlPath = ''
                metadataXmlSize = 0
                callback.iiGetLatestVaultMetadataXml(vault_collection, metadataXmlPath, metadataXmlSize)
                data_name = metadataXmlPath.split('/')[-1]  
                
                if data_name != "":
                    transformVaultMetadataXmlToJson(callback, rods_zone, vault_collection, group_name, data_name)
        
        except Exception as e:
            log.write(callback, str(e))
            pass

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id = coll_id + 1
    else:
        # All done.
        coll_id = 0

    return coll_id


def rule_uu_vault_xml_to_json_check_vault_metadata_xml_for_transformation_to_json(rule_args, callback, rei):
    """Convert vault metadata XML to JSON - batchwise.

    :param coll_id: First COLL_ID to check - initial =0
    :param batch: Batch size, <= 256
    :param pause: Pause between checks (float)
    :param delay: Delay between batches in seconds
    """
    import session_vars

    coll_id = int(rule_args[0])
    batch = int(rule_args[1])
    pause = float(rule_args[2])
    delay = int(rule_args[3])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one	batch of metadata schemas.
    # If no more collections are found, the function returns 0
    coll_id = iiCheckVaultMetadataXmlForTransformationToJsonBatch(callback, rods_zone, coll_id, batch, pause)

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "rule_uu_vault_xml_to_json_check_vault_metadata_xml_for_transformation_to_json('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")
