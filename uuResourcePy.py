# \file      uuResourcesPy.py
# \brief     Functions for handling schema updates within any yoda-metadata.xml.
# \author    Lazlo Westerhof
# \author    Felix Croes
# \author    Harm de Raaff
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# @TODO - welke moeten mee??
import os
from datetime import datetime
from collections import namedtuple
# from enum import Enum
# import hashlib
# import base64
import json
import irods_types
# from irods.meta import iRODSMeta
# import lxml.etree as etree
# import xml.etree.ElementTree as ET

import time

## Hoe met constanten om te gaan?
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


# \Brief Get JSON represenation of resource and its tier info
def uuRuleGetResourceTierData(rule_args, callback, rei):
    resourceName = rule_args[0]

    tierName = getTierOnResourceName(resourceName, callback)

    rule_args[1] = json.dumps({"resourceName":resourceName,"org_storage_tier":tierName})


# \Brief Get all resources and their tier data as a json representation:
# resourceName
# resourceId
# org_storage_tier

def uuRuleGetResourcesAndTierData(rule_args, callback, rei): 

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
        for row in range(0, result.rowCnt):
            resourceId =  result.sqlResult[0].row(row)
            resourceName = result.sqlResult[1].row(row)
            tierName = getTierOnResourceName(resourceName, callback) 
            resourceList.append({'resourceName':resourceName, 'resourceId':resourceId, 'org_storage_tier':tierName})

    rule_args[0] = json.dumps(resourceList)


# \Brief: Get json representation for storage data for a period of 12 months for a specific group
# Storage isper month and tier 
# Format is "month=12-tier=Standard": "222222222222"

def uuRuleGetMonthStoragePerTierForGroup(rule_args, callback, rei):
    groupName = rule_args[0]
    currentMonth = int(rule_args[1])  # this is the month that came from the frontend 
 
    allStorage = [] # list of all month-tier combinations present including their storage size

    # per month gather month/tier/storage information from metadata:
    # metadata-attr-name = UUMETADATASTORAGEMONTH + '01'...'12'
    # metadata-attr-val = [category,tier,storage] ... only tier and storage required wihtin this code

    for counter in range(0,11):
        referenceMonth = currentMonth - counter
        if referenceMonth < 1:
            referenceMonth = referenceMonth + 12

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
                data_size = temp[2] # no construction for summation required in this case

                key = 'month=' + str(referenceMonth) + '-tier=' + tierName
                allStorage.append({key:data_size})

    callback.writeString("serverLog", json.dumps(allStorage))
    rule_args[2] = json.dumps(allStorage)


# \Brief collect storage data for ALL categories
def uuRuleGetMonthlyStorageStatistics(rule_args, callback, rei):
    categories = getCategories(callback)

    rule_args[0] = getMonthlyCategoryStorageStatistics(categories, callback)


# \Brief collect storage data for a Datamanager
def uuRuleGetMonthlyStorageStatisticsDatamanager(rule_args, callback, rei):
    datamanagerUser = rule_args[0]
    categories = getCategoriesDatamanager(datamanagerUser, callback)

    rule_args[1] = getMonthlyCategoryStorageStatistics(categories, callback)

# \Brief Get all groups for all categories a person is datamanager of
def uuRuleGetAllGroupsForDatamanager(rule_args, callback, rei):
    datamanagerUser = rule_args[0]
    categories = getCategoriesDatamanager(datamanagerUser, callback)

    datamanagerGroups = getGroupsOnCategories(categories, callback)

    rule_args[1] = json.dumps(datamanagerGroups)


#----------------------------------------------------------------------------------- End of interface layer from irods rule system

# \Brief collect storage stats of last month only
# json presentation
#  Array ( [0] => Array ( [category] => initial [tier] => Standard [storage] => 15777136 )

def getMonthlyCategoryStorageStatistics(categories, callback):
    month = '%0*d' % (2, datetime.now().month)

    callback.writeString("serverLog", "getMonthlyCategoryStorateStatistics for month: " + month)

    metadataName = UUMETADATASTORAGEMONTH + month

    storageDict = {}

    for category in categories:
        ret_val = callback.msiMakeGenQuery(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category+ "\",%' AND META_USER_ATTR_NAME = '" + metadataName + "'",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        if result.rowCnt != 0:
        # hier wordt door alle groepen gezocht, geordend van een category.
        # per tier moet worden gesommeerd om totale hoeveelheid storage op een tier te verkrijgen.

            for row in range(0, result.rowCnt):
                attrValue = result.sqlResult[0].row(row)

                temp = json.loads(attrValue)
                category = temp[0]
                tier = temp[1]
                storage = int(temp[2])

                callback.writeString("serverLog", "    Category: %s" % (category))
                callback.writeString("serverLog", "    Tier: %s" % (tier))
                callback.writeString("serverLog", "    STORAGE: %s" % (str(storage)))

                # Aggregation of storage amount per category/tier
                if category in storageDict:
                    if tier in storageDict[category]:
                        # Add storage to present storage already for cat/tier
                        storageDict[category][tier] = storageDict[category][tier]  + storage
                    else:
                        storageDict[category][tier] = storage
                else:
                    storageDict[category] = {tier:storage}

    # prepare for json output, convert storageDict into dict with keys
    allStorage = []       
    for category in storageDict:
        for tier in storageDict[category]:
            #callback.writeString("serverLog", 'Cat: ' + category + ' tier: ' + tier + ' storage: ' + str(storageDict[category][tier]) )
            allStorage.append({'category': category, 'tier': tier, 'storage':str(storageDict[category][tier])})

    return json.dumps(allStorage)

# \Brief Get all groups belonging to all given categories  
def getGroupsOnCategories(categories, callback):
    groups = []

    for category in categories:

        ret_val = callback.msiMakeGenQuery(
            "USER_NAME",
            "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        callback.writeString("serverLog", 'Group records found: ' + str(result.rowCnt))


        if result.rowCnt != 0:
            for row in range(0, result.rowCnt):
               groups.append(result.sqlResult[0].row(row))

    return groups


# \Brief Get all categories for curent datamanager
def getCategoriesDatamanager(datamanagerName, callback):
    categories = []

    ret_val = callback.msiMakeGenQuery(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]
    
    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    callback.writeString("serverLog", 'Category records found: ' + str(result.rowCnt))

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
           # @TODO membership still has to be checked

           datamanagerGroupname = result.sqlResult[0].row(row)
           temp = datamanagerGroupname.split('-')  # 'datamanager-initial' is groupname of datamanager, second part is category 
           callback.writeString("serverLog", 'Datamanagergroupname: ' + datamanagerGroupname)
           categories.append(temp[1])

    return categories

# \Brief get all categories currently present
def getCategories(callback):
    ret_val = callback.msiMakeGenQuery(
        " META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND  META_USER_ATTR_NAME  = 'category'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    callback.writeString("serverLog", 'Category records found: ' + str(result.rowCnt))

    categories = []

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
           categories.append(result.sqlResult[0].row(row))
    
    return categories

# \Brief Get Tiername, if present, for given resource
# If not present, fall back to default tier name 
def getTierOnResourceName(resourceName, callback):
    tierName = UUDEFAULTRESOURCETIER # Add default tier as this might not be present in database.

    # find (possibly present) tier for this resource
    ret_val = callback.msiMakeGenQuery(
        "RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE",
        "RESC_NAME = '" + resourceName + "' AND META_RESC_ATTR_NAME = '" + UURESOURCETIERATTRNAME + "'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            tierName = result.sqlResult[3].row(row)

    return tierName



#------------------------------------- test functions @TODO weghalen
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


