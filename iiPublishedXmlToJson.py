import xmltodict
import os

from json import loads
from collections import OrderedDict



# \brief Get the content of a yoda-metadata.xml file and return parsed into a dict 
#
# \param[in] path	yoda-metadata.xml
#
# \return Dict holding data
#
def PUBgetMetadataXmlAsDict(callback, path):
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

    # callback.writeString('serverLog', xmlText)
	
    return xmltodict.parse(xmlText)



# \brief Get Json Schema of category and return as (ordered!) dict
#
# \param[in] rods_zone
# \param[in] category    name of category the metadata belongs to
#
# \return dict hodling the category JSONSchema
#
def PUBgetMetadaJsonDict(callback, yoda_json_path):   
	
    coll_name, data_name = os.path.split(yoda_json_path)

    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open JSON file
    ret_val = callback.msiDataObjOpen('objPath=' + yoda_json_path, 0)
    fileHandle = ret_val['arguments'][1]
	
    # Read JSON 
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close JSON schema.
    callback.msiDataObjClose(fileHandle, 0)

    # Parse JSON into dict.
    read_buf = ret_val['arguments'][2]
    jsonText = ''.join(read_buf.buf)

    # Use the hook to keep ordering of elements as in metadata.json
    return json.loads(jsonText, object_pairs_hook=OrderedDict)








# \brief Read yoda-metadata.json from vault and return as (ordered!) dict
#
# \param[in] rods_zone
# \param[in] category    name of category the metadata belongs to
#
# \return dict hodling the category JSONSchema
#
def PUBgetActiveJsonSchemaAsDict(callback, rods_zone, category):   ## irods-ruleset-uu function in uuResources.py

    json_schema_path = '/' +  rods_zone + '/yoda/schemas/' + category + '/metadata.json'

    coll_name, data_name = os.path.split(json_schema_path)

    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open JSON schema for the category
    ret_val = callback.msiDataObjOpen('objPath=' + json_schema_path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read JSON schema.
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close JSON schema.
    callback.msiDataObjClose(fileHandle, 0)

    # Parse JSON into dict.
    read_buf = ret_val['arguments'][2]
    jsonText = ''.join(read_buf.buf)

    # callback.writeString('serverLog', jsonText)

    # Use the hook to keep ordering of elements as in metadata.json
    return json.loads(jsonText, object_pairs_hook=OrderedDict)






# \brief turn yoda-metadata.xml into Json
#
# \param[in] dictSchema  JSON schema that yoda-metadata.xml must be transformed to
# \param[in] xmlData     dict with all data in yoda-metadata.xml
#
# \return JSON formatted string holding content of yoda-metadata.xml
#
def PUBtransformYodaXmlDataToJson(callback, dictSchema, xmlData):
    jsonDict = {}

    for elementName in dictSchema['properties']:
        elementInfo = dictSchema['properties'][elementName]

        try:  ## CHECK IF DATA IS PRESENT
            data = xmlData['metadata'][elementName]

            if isinstance(data, list):  # Multiple data entries for given elemenent

	        totalElementList = []
                newData = {}
                for dataItem in data:  ### MULTIPLE ENTRIES IN DATA
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
                                        subIsMultiple = False;
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


                    else:  ## SINGLE ENTRY e.g. Discipline
                        totalElementList.append(dataItem)

                jsonDict[elementName] = totalElementList

            elif isinstance(data, dict):  # Single structure
                fieldIsMultiple = (elementInfo['type'] == 'array')
                newData = {}

                try:
                    # Als er sprake is van ['items'] +> dan is vanaf het hoogste niveau een structuur bekend van subproperties // compounds
                    if elementInfo['items']['yoda:structure'] == 'subproperties':
                        counter = 0
			
                        for subElement,subElementInfo in elementInfo['items']['properties'].items():   # keys(): #items()):
	
                            if counter == 0:  # MAIN PART of subproperty structure  ! in itself always a single value
                                # Added these extra variables for clearer name purposes as there is a distinction between main/sub elements
                                mainElement = subElement
                                mainElementVal = data[subElement]
                                newData[mainElement] = mainElementVal  # # MAINPART of subproperty structure IS ALWAYS SINGULAR!
                            else:  # SUB PART of subproperty structure - corresponding data is beneath <Properties> tag within XML
                                subPropertyElement = subElement

                                # I this a single or multiple subproperty element??
                                subIsMultiple = False;
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
                                    if subIsMultiple and not isinstance(data['Properties'][subPropertyElement],list):
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
            else:
                try:
                    jsonDict[elementName] = data
                except KeyError:
                    pass

        except KeyError:  # No data present for this element
            pass

    # Hardcoding allowed here 
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
    
    return json.dumps(jsonDict)




# \brief Convert current metadata.xml to json
#
# \param[in] rods_zone  Zone name
# \param[in] vault_collection  Collection name of metadata XML
# \param[in] xml_data_name  Data name of metadata XML that requires transformation
# \param[in] data_name_json  Name of data object to be created containing the 
##
def transformPublishedMetadataXmlToJson(callback, rods_zone, publish_collection, xml_data_name, data_name_json):
    # This function simply transforms given data_name to a Json data object. 
	# No further intelligence required further. 
	# Perhaps handling within vault??
	
	ofFlags = ''
	json_file = publish_collection + '/' + data_name_json

	ret_val = callback.msiDataObjCreate(json_file, ofFlags, 0)
	
	#copyACLsFromParent(callback, json_file, "default")

        xmlDataDict = getMetadataXmlAsDict(callback, publish_collection + "/" + xml_data_name)
        
	# take category incuding version from declared namespace in xml
	category_version = xmlDataDict['metadata']['@xmlns'].split('/')[-1]

	dictSchema = getActiveJsonSchemaAsDict(callback,rods_zone, category_version)

	newJsonDataString = transformYodaXmlDataToJson(callback, dictSchema, xmlDataDict)
	
	fileHandle = ret_val['arguments'][2]
	callback.msiDataObjWrite(fileHandle, newJsonDataString, 0)
	callback.msiDataObjClose(fileHandle, 0)

	callback.writeString("serverLog", "[ADDED METADATA.JSON AFTER TRANSFORMATION] %s" % (json_file))



# \brief Loop through all metadata xml data objects within '/tempZone/yoda/publication'.
#        If NO corresponding json is found in that collection, the corresponding yoda-metadata.xml must be converted to json as an extra file - yoda-metadata.json.
#        The resulting file must be copied to moai collection as well
#
# \param[in] rods_zone Zone name
# \param[in] data_id   data id to start searching from
# \param[in] batch     Batch size, <= 256
# \param[in] pause     Pause between checks (float)
# \param[in] publicHost, yodaInstance, yodaPrefix are required for secure copy from /publication area to MOAI
#
# \return data_id to continue with in next batch.
# If data_id =0, no more data objects were found. 
# Batch is finished
#
def iiCheckPublishedMetadataXmlForTransformationToJsonBatch(callback, rods_zone, data_id, batch, pause, publicHost, yodaInstance, yodaPrefix):

    publication_collection = '/' + rods_zone + '/yoda/publication'
    iter = genquery.row_iterator(
        "ORDER(DATA_ID), DATA_NAME, COLL_ID",
        "COLL_NAME = '%s' AND DATA_NAME like '%%.xml' AND DATA_ID >= '%d'" % (publication_collection, data_id),
        genquery.AS_LIST, callback
    )

    # Check each collection in batch.
    for row in iter:
	data_id = int(row[0])
        data_name_xml = row[1]
        coll_id = int(row[2])
        pathParts = coll_name.split('/')
        data_name_no_extension = os.path.splitext(data_name)[0] # the base name of the data object without extension
        data_name_json = data_name_no_extension + '.json'

        try:
	    # First make sure that no metadata json file exists already in the published collection .
	    # If so, no transformation is required and the json file needs not be copied into the MOAI area.

	    jsonFound = False
	    iter2 = genquery.row_iterator(
		 "ORDER(COLL_ID), COLL_NAME",
		 "DATA_NAME = '%s' AND COLL_ID = '%d'" % (data_name_json, coll_id),
		 genquery.AS_LIST, callback
	    )
	    for row2 in iter2:
		jsonFound = True
		break

	    if jsonFound == False:
                # At this moment only default schema is used. So not required to figure out which schema is necessary
	        transformPublishedMetadataXmlToJson(callback, rods_zone, publication_collection, data_name_xml, data_name_json)

                callback.iiCopyTransformedPublicationToMOAI(data_name_json, publication_collection, publicHost, yodaInstance, yodaPrefix)
        except:
            pass

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next data_id to check must have a higher DATA_ID
        data_id = data_id + 1
    else:
        # All done.
        data_id = 0

    return data_id


# \brief Convert published metadata XML that residedes in 'published' collection to JSON - batchwise
#
# \param[in] data_id  first data to check - initial =0
# \param[in] batch    batch size, <= 256
# \param[in] pause    pause between checks (float)
# \param[in] delay    delay between batches in seconds
# \param[in] publicHost,yodaInstance,yodaPrefix are required for secure copy from /publication area to MOAI
#
def iiCheckPublishedMetadataXmlForTransformationToJson(rule_args, callback, rei):
    coll_id = int(rule_args[0])
    batch = int(rule_args[1])
    pause = float(rule_args[2])
    delay = int(rule_args[3])
    publicHost = rule_args[4] 
    yodaInstance = rule_args[5] 
    yodaPrefix = rule_args[6]
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one	batch of metadata schemas.
    # If no more data_ids are found in the main/single publication folder, the function returns 0
    data_id = iiCheckPublishedMetadataXmlForTransformationToJsonBatch(callback, rods_zone, data_id, batch, pause, publicHost, yodaInstance, yodaPrefix)

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "iiCheckPublishedMetadataXmlForTransformationToJson('%d', '%d', '%f', '%d')" % (data_id, batch, pause, delay, publicHost, yodaInstance, yodaPrefix),
            "")




