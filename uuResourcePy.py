# \file      uuResourcesPy.py
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
from irods.meta import iRODSMeta
import lxml.etree as etree
import xml.etree.ElementTree as ET

import time

UUORGMETADATAPREFIX = 'org_'
UUSYSTEMCOLLECTION = "/yoda"

# \constant  UUREVISIONCOLLECTION   irods path where all revisions will be stored
UUREVISIONCOLLECTION = UUSYSTEMCOLLECTION + "/revisions"

# \RESOURCE AND TIER MANAGEMENT
# \Default name for a tier when none defined yet
UUDEFAULTRESOURCETIER = 'Standard'

# \Metadata attribute for storage tier name
UURESOURCETIERATTRNAME = UUORGMETADATAPREFIX + 'storage_tier'

# \Metadata for calculated storage month
UUMETADATASTORAGEMONTH =  UUORGMETADATAPREFIX + 'storage_data_month'

#--------------------- Interface layer from irods rules


# 
def uuRuleGetMonthStoragePerTier(rule_args, callback, rei):
    groupName = rule_args[0]
    currentMonth = int(rule_args[1])
 
    all = [{"month=12-tier=Standard": "222222222222"}, {"month=2-tier=Standard": "9999999999999"}]
    allStorage = []
    rule_args[2] =  json.dumps(all) #  '[{"month=12-tier=Standard": "5555555555555"}, {"month=2-tier=Standard": "9999999999999"}]'

    # per month gather all present storage information and decypher 

    for counter in range(0,11):
        referenceMonth = currentMonth - counter
        if referenceMonth < 1:
            referenceMonth = referenceMonth + 12

        # referenceMonth = '%0*d' % (2, referenceMonth) 
        metadataAttrNameRefMonth = UUMETADATASTORAGEMONTH + '%0*d' % (2, referenceMonth)

        callback.writeString("serverLog", metadataAttrNameRefMonth + '-' + groupName) 

        ret_val = callback.msiMakeGenQuery(
            "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + groupName+ "'",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        callback.writeString("serverLog", 'Metadata records count: ' + str(result.rowCnt))
        if result.rowCnt != 0:
            for row in range(0, result.rowCnt):
                data = result.sqlResult[0].row(row)
                temp = json.loads(data)
                callback.writeString("serverLog", 'StorageData: ' + metadataAttrNameRefMonth + ' ->' +  temp[0] + ' ->' + data)
              
                tierName = temp[1]
                data_size = temp[2]

                key = 'month=' + str(referenceMonth) + '-' + tierName
                allStorage.append({key:data_size})

    callback.writeString("serverLog", json.dumps(allStorage))
    rule_args[2] = json.dumps(all) #json.dumps(allStorage)


#---------- End of interface layer from irods rules






#------------------------------------- test functions
def uuTest(rule_args, callback, rei):
    testVal = rule_args[0]
    callback.writeString("serverLog", "[uuTest]arguments %s" % (rule_args))

    coll_name = "/tempZone/home/research-initial"
    ret_val = callback.msiMakeGenQuery(
        "SUM(DATA_SIZE)",
        "COLL_NAME = '%s'" % (coll_name),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    data_size = 0
    callback.writeString("serverLog", str(result.rowCnt))
    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            data_size = result.sqlResult[0].row(row)
            callback.writeString("serverLog", "size: %s" %(str(data_size)))
    
    #--------------------------------------------------------------------------------------------  TIERS - uuListResourceTiers()
    callback.writeString("serverLog", UURESOURCETIERATTRNAME)

    metaName = UURESOURCETIERATTRNAME;
    
    ret_val = callback.msiMakeGenQuery(
        "META_RESC_ATTR_VALUE",
        "META_RESC_ATTR_NAME = '" + metaName + "'" ,
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    callback.writeString("serverLog", 'Tiers records found: ' + str(result.rowCnt))

    tierList = list()

    if result.rowCnt != 0:
        # hier wordt door alle groepen gezocht, geordend van een category.
        # per tier moet worden gesommeerd om totale hoeveelheid storage op een tier te verkrijgen.
        for row in range(0, result.rowCnt):
           tierName = result.sqlResult[0].row(row)
           if tierName not in tierList:
               tierList.append(tierName)
           callback.writeString("serverLog", tierName)     

    if UUDEFAULTRESOURCETIER not in tierList:
        tierList.append(UUDEFAULTRESOURCETIER)
    
    callback.writeString("serverLog", "-".join(tierList)) 
    #-------------------------------------------------------------------------------------------- RESOURCE - uuListResources()
    ret_val = callback.msiMakeGenQuery(
        "RESC_ID, RESC_NAME",
        "",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    callback.writeString("serverLog", 'Resource records found: ' + str(result.rowCnt))

    resourceList = list()

    if result.rowCnt != 0:
        # hier wordt door alle groepen gezocht, geordend van een category.
        # per tier moet worden gesommeerd om totale hoeveelheid storage op een tier te verkrijgen.
        for row in range(0, result.rowCnt):
           resourceID =  result.sqlResult[0].row(row)
           resourceName = result.sqlResult[1].row(row)
           resourceList.append({resourceID:resourceName})
           callback.writeString("serverLog", resourceName + ': ' + resourceID)

    for resource in resourceList:
        for key in resource:
           callback.writeString("serverLog", key + '-' + resource[key])   

    #---------------------------------------------------------------------------------------------- uuListResourcesAndStatisticData()

    allRescStats = list()

    metaName = UURESOURCETIERATTRNAME

    for resource in resourceList:
        for key in resource:
            resourceID = key
            resourceName = resource[key]

            ret_val = callback.msiMakeGenQuery(
                "RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE",
                "RESC_NAME = '" + resourceName + "' AND META_RESC_ATTR_NAME = '" + metaName + "'",
                irods_types.GenQueryInp())
            query = ret_val["arguments"][2]

            ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
            result = ret_val["arguments"][1]

            if result.rowCnt != 0:
                for row in range(0, result.rowCnt):
                    tierAttrName = result.sqlResult[2].row(row)
                    tierAttrVal = result.sqlResult[3].row(row)
                    allRescStats.append({resourceID:resourceName, tierAttrName:tierAttrVal})
                    callback.writeString("serverLog", '+++++++++' + resourceName + ': ' + resourceID + '  ' + tierAttrVal + ' ' + tierAttrVal)


    #--------------------------------------------------------------------------------------
    callback.writeString("serverLog", "------------------------ ophalen data category,tier,storage ")
    # SELECT META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME 
    #				WHERE META_USER_ATTR_NAME = '*metadataName'
    #				AND META_USER_ATTR_VALUE like '[\"*categoryName\",%%'  )

    # category = "initial" 
    category = "intake-intake"
    ret_val = callback.msiMakeGenQuery(
        "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
        "META_USER_ATTR_VALUE like '[\"" + category+ "\",%' ",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    callback.writeString("serverLog", 'Metadata records count: ' + str(result.rowCnt))
    if result.rowCnt != 0:
        storageDict = {}
        # hier wordt door alle groepen gezocht, geordend van een category.
        # per tier moet worden gesommeerd om totale hoeveelheid storage op een tier te verkrijgen.

        for row in range(0, result.rowCnt):
            attrValue = result.sqlResult[0].row(row)
            month = result.sqlResult[1].row(row)[-2:]
            userName = result.sqlResult[2].row(row)
            userGroupName = result.sqlResult[3].row(row)
            callback.writeString("serverLog", "Month %s" % (month))
            callback.writeString("serverLog", "    userName userGroupName %s %s" % (userName, userGroupName))

            # attrValue holds 3 values:  category,tier,storage
            listValues = attrValue.split('","')
            category = listValues[0][2:]
            tier = listValues[1]
            storage = int(listValues[2][:-2])
             
            callback.writeString("serverLog", "    Category: %s" % (category))
            callback.writeString("serverLog", "    Tier: %s" % (tier))
            callback.writeString("serverLog", "    STORAGE: %s" % (str(storage)))

            # totalize per 
	    #   1) month
            #	2) category 
            #   3) per tier         


            if month in storageDict:
                if category in storageDict[month]:
                    if tier in storageDict[month][category]:
                        # Add storage to present storage already
                        storageDict[month][category][tier] = storageDict[month][category][tier]  + storage
                    else:
                        storageDict[month][category][tier] = storage
                else:
                    storageDict[month][category] = {tier:storage}

            else: 
                storageDict[month] = {category: {tier: storage}}


