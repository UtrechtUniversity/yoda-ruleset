# \file      uuResources.py
# \brief     Functions for statistics module - in essence a python extension directly related to uuResources.r
# \author    Lazlo Westerhof
# \author    Felix Croes
# \author    Harm de Raaff
# \copyright Copyright (c) 2018-2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import os
from datetime import datetime
import json
import irods_types


# \brief Get JSON represenation of resource and its tier info
#
def uuRuleGetResourceTierData(rule_args, callback, rei):
    resourceName = rule_args[0]

    tierName = getTierOnResourceName(resourceName, callback)

    rule_args[1] = json.dumps({"resourceName": resourceName,
                               "org_storage_tier": tierName})


# \brief Get all resources and their tier data as a json representation:
#
def uuRuleGetResourcesAndTierData(rule_args, callback, rei):
    ret_val = callback.msiMakeGenQuery(
        "RESC_ID, RESC_NAME",
        "",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    resourceList = list()

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            resourceId = result.sqlResult[0].row(row)
            resourceName = result.sqlResult[1].row(row)
            tierName = getTierOnResourceName(resourceName, callback)
            resourceList.append({'resourceName': resourceName,
                                 'resourceId': resourceId,
                                 'org_storage_tier': tierName})

    rule_args[0] = json.dumps(resourceList)


# \brief Get json representation for storage data for a period of 12 months for a specific group
# Storage is per month and tier
# Format is "month=12-tier=Standard": "222222222222"
#
def uuRuleGetMonthStoragePerTierForGroup(rule_args, callback, rei):
    groupName = rule_args[0]
    currentMonth = int(rule_args[1])  # this is the month that came from the frontend

    allStorage = []  # list of all month-tier combinations present including their storage size

    # per month gather month/tier/storage information from metadata:
    # metadata-attr-name = UUMETADATASTORAGEMONTH + '01'...'12'
    # metadata-attr-val = [category,tier,storage] ... only tier and storage required wihtin this code
    for counter in range(0, 11):
        referenceMonth = currentMonth - counter
        if referenceMonth < 1:
            referenceMonth = referenceMonth + 12

        metadataAttrNameRefMonth = UUMETADATASTORAGEMONTH + '%0*d' % (2, referenceMonth)

        ret_val = callback.msiMakeGenQuery(
            "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + groupName + "'",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        callback.writeString("serverLog", 'Metadata records count: ' + str(result.rowCnt))
        if result.rowCnt != 0:
            for row in range(0, result.rowCnt):
                data = result.sqlResult[0].row(row)
                temp = json.loads(data)

                tierName = temp[1]
                data_size = temp[2]  # no construction for summation required in this case

                key = 'month=' + str(referenceMonth) + '-tier=' + tierName
                allStorage.append({key: data_size})

    rule_args[2] = json.dumps(allStorage)


# \brief collect storage data for ALL categories
#
def uuRuleGetMonthlyStorageStatistics(rule_args, callback, rei):
    categories = getCategories(callback)

    rule_args[0] = getMonthlyCategoryStorageStatistics(categories, callback)


# \brief collect storage data for a Datamanager
#
def uuRuleGetMonthlyStorageStatisticsDatamanager(rule_args, callback, rei):
    datamanagerUser = rule_args[0]
    categories = getCategoriesDatamanager(datamanagerUser, callback)

    rule_args[1] = getMonthlyCategoryStorageStatistics(categories, callback)


# \brief Get all groups for all categories a person is datamanager of
#
def uuRuleGetAllGroupsForDatamanager(rule_args, callback, rei):
    datamanagerUser = rule_args[0]
    categories = getCategoriesDatamanager(datamanagerUser, callback)

    datamanagerGroups = getGroupsOnCategories(categories, callback)

    rule_args[1] = json.dumps(datamanagerGroups)


# \brief collect storage stats for all twelve months based upon categories a user is datamanager of
#  - Category
#  - Subcategory
#  - Groupname
#  - Tier
#  - 12 columns, one per month, with used storage count in bytes

def uuRuleExportMonthlyCategoryStatisticsDM(rule_args, callback, rei):
    datamanagerUser = rule_args[0]
    categories = getCategoriesDatamanager(datamanagerUser, callback)
    allStorage = []

    # Select a full year by not limiting UUMETADATASTORAGEMONTH to a perticular month. But only on its presence.
    # There always is a maximum of one year of history of storage data
    for category in categories:
        groupToSubcategory = {}

        ret_val = callback.msiMakeGenQuery(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category + "\",%' AND META_USER_ATTR_NAME like  '" + UUMETADATASTORAGEMONTH + "%'",
            irods_types.GenQueryInp())
        query = ret_val["arguments"][2]

        ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
        result = ret_val["arguments"][1]

        if result.rowCnt != 0:
            for row in range(0, result.rowCnt):
                attrValue = result.sqlResult[0].row(row)

                month = result.sqlResult[1].row(row)
                month = str(int(month[-2:]))  # the month storage data is about, is taken from the attr_name of the AVU
                groupName = result.sqlResult[3].row(row)

                # Determine subcategory on groupName
                try:
                    subcategory = groupToSubcategory[groupName]
                except KeyError:
                    catInfo = groupGetCategoryInfo(groupName, callback)
                    subcategory = catInfo['subcategory']
                    groupToSubcategory[groupName] = subcategory

                temp = json.loads(attrValue)
                category = temp[0]
                tier = temp[1]
                storage = int(temp[2])

                allStorage.append({'category': category, 'subcategory': subcategory, 'groupname': groupName, 'tier': tier, 'month': month, 'storage': str(storage)})

    rule_args[1] = json.dumps(allStorage)


# \brief Get category and subcategory for a group
#
# \return dict with indices 'category' and 'subcategory'
def groupGetCategoryInfo(groupName, callback):
    category = ''
    subcategory = ''

    ret_val = callback.msiMakeGenQuery(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + groupName + "' AND  META_USER_ATTR_NAME LIKE '%category'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            attrName = result.sqlResult[0].row(row)
            attrValue = result.sqlResult[1].row(row)

            if attrName == 'category':
                category = attrValue
            elif attrName == 'subcategory':
                subcategory = attrValue

    return {'category': category, 'subcategory': subcategory}


# \brief collect storage stats of last month only
# Storage is summed up for each category/tier combination
# json presentation
#  Array ( [0] => Array ( [category] => initial [tier] => Standard [storage] => 15777136 )
def getMonthlyCategoryStorageStatistics(categories, callback):
    month = '%0*d' % (2, datetime.now().month)
    metadataName = UUMETADATASTORAGEMONTH + month
    storageDict = {}

    for category in categories:
        ret_val = callback.msiMakeGenQuery(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category + "\",%' AND META_USER_ATTR_NAME = '" + metadataName + "'",
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
                storage = int(float(temp[2]))

                try:
                    storageDict[category][tier] = storageDict[category][tier] + storage
                except KeyError:
                    callback.writeString('serverLog', 'Exception')
                    # if key error, can be either category or category/tier combination is missing
                    try:
                        storageDict[category][tier] = storage
                    except KeyError:
                        storageDict[category] = {tier: storage}

    # prepare for json output, convert storageDict into dict with keys
    allStorage = []

    for category in storageDict:
        for tier in storageDict[category]:
            allStorage.append({'category': category,
                               'tier': tier,
                               'storage': str(storageDict[category][tier])})

    return json.dumps(allStorage)


# \brief Get all groups belonging to all given categories
#
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

        metadataAttrNameRefMonth = UUMETADATASTORAGEMONTH + '%0*d' % (2, datetime.now().month)

        if result.rowCnt != 0:
            for row in range(0, result.rowCnt):
                groupName = result.sqlResult[0].row(row)

                ret_val = callback.msiMakeGenQuery(
                    "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
                    "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + groupName + "'",
                    irods_types.GenQueryInp())
                query = ret_val["arguments"][2]

                ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
                result2 = ret_val["arguments"][1]
                data_size = 0
                if result2.rowCnt != 0:
                    for row2 in range(0, result2.rowCnt):
                        data = result2.sqlResult[0].row(row2)
                        temp = json.loads(data)
                        data_size = data_size + int(temp[2])  # no construction for summation required in this case

                groups.append([result.sqlResult[0].row(row), data_size])

    return groups


# \brief Get all categories for curent datamanager
#
def getCategoriesDatamanager(datamanagerName, callback):
    categories = []

    ret_val = callback.msiMakeGenQuery(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            # @TODO membership still has to be checked
            datamanagerGroupname = result.sqlResult[0].row(row)
            temp = datamanagerGroupname.split('-')  # 'datamanager-initial' is groupname of datamanager, second part is category
            categories.append(temp[1])

    return categories


# \brief get all categories currently present
#
def getCategories(callback):
    ret_val = callback.msiMakeGenQuery(
        " META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND  META_USER_ATTR_NAME  = 'category'",
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    categories = []

    if result.rowCnt != 0:
        for row in range(0, result.rowCnt):
            categories.append(result.sqlResult[0].row(row))

    return categories


# \brief Get Tiername, if present, for given resource
# If not present, fall back to default tier name
#
def getTierOnResourceName(resourceName, callback):
    tierName = UUDEFAULTRESOURCETIER  # Add default tier as this might not be present in database.

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
