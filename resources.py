# -*- coding: utf-8 -*-
"""Functions for statistics module - in essence a python extension directly related to uuResources.r."""

__copyright__ = 'Copyright (c) 2018-2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

from util import *
import meta_form


__all__ = ['api_uu_resource_groups_dm',
           'api_uu_resource_monthly_stats_dm',
           'api_uu_resource_monthly_category_stats_export_dm',
           'api_uu_resource_monthly_stats',
           'api_uu_resource_resource_and_tier_data',
           'api_uu_resource_tier',
           'api_uu_resource_get_tiers',
           'api_uu_resource_save_tier',
           'api_uu_resource_user_get_type',
           'api_uu_resource_user_research_groups',
           'api_uu_resource_user_is_datamanager',
           'api_uu_resource_full_year_group_data']


@api.make()
def api_uu_resource_save_tier(ctx, resource_name, tier_name):
    if user.user_type(ctx) != 'rodsadmin':
        return {'status': 'not_allowed',
                'status_info': 'Insufficient permissions'}

    res = ctx.uuSetResourceTier(resource_name, tier_name, '', '')

    return {'status': res['arguments'][2],
            'status_info': res['arguments'][3]}


@api.make()
def api_uu_resource_full_year_group_data(ctx, group_name, current_month):
    # Check permissions for this function
    # Member of this group?
    member_type = meta_form.user_member_type(ctx, group_name, user.full_name(ctx))
    if member_type not in ['reader', 'normal', 'manager']:
        category = meta_form.group_category(ctx, group_name)
        if not meta_form.user_is_datamanager(ctx, category, user.full_name(ctx)):
            if user.user_type(ctx) != 'rodsadmin':
                return api.Error('not_allowed', 'Insufficient permissions')

    allStorage = []  # list of all month-tier combinations present including their storage size

    # per month gather month/tier/storage information from metadata:
    # metadata-attr-name = constants.UUMETADATASTORAGEMONTH + '01'...'12'
    # metadata-attr-val = [category,tier,storage] ... only tier and storage required within this code
    for counter in range(0, 11):
        referenceMonth = current_month - counter
        if referenceMonth < 1:
            referenceMonth = referenceMonth + 12

        metadataAttrNameRefMonth = constants.UUMETADATASTORAGEMONTH + '%0*d' % (2, referenceMonth)

        iter = genquery.row_iterator(
            "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + group_name + "'",
            genquery.AS_LIST, ctx
        )

        for row in iter:
            data = jsonutil.parse(row[0])

            tierName = data[1]
            data_size = data[2]  # no construction for summation required in this case

            key = 'month=' + str(referenceMonth) + '-tier=' + tierName
            allStorage.append({key: data_size})

    return allStorage


@api.make()
def api_uu_resource_user_get_type(ctx):
    return user.user_type(ctx)


@api.make()
def api_uu_resource_user_research_groups(ctx):
    groups = []
    user_name = user.name(ctx)
    user_zone = user.zone(ctx)

    iter = genquery.row_iterator(
        "USER_GROUP_NAME",
        "USER_NAME = '" + user_name + "' AND  USER_ZONE = '" + user_zone + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if row[0].startswith('research-'):
            groups.append(row[0])

    groups.sort()
    return groups


@api.make()
def api_uu_resource_user_is_datamanager(ctx):
    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        group_name = row[0]
        if group.exists(ctx, group_name) and user.is_member_of(ctx, group_name):
            return 'yes'

    return 'no'


@api.make()
def api_uu_resource_get_tiers(ctx):
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    tiers = [constants.UUDEFAULTRESOURCETIER]

    iter = genquery.row_iterator(
        "META_RESC_ATTR_VALUE",
        "META_RESC_ATTR_NAME = '" + constants.UURESOURCETIERATTRNAME + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if not row[0] == constants.UUDEFAULTRESOURCETIER:
            tiers.append(row[0])

    return tiers


@api.make()
def api_uu_resource_tier(ctx, res_name):
    """Get the tier belonging to the given resource."""
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    return get_tier_by_resource_name(ctx, res_name)


@api.make()
def api_uu_resource_resource_and_tier_data(ctx):
    """Get all resources and their tier data."""
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    resourceList = list()

    iter = genquery.row_iterator(
        "RESC_ID, RESC_NAME",
        "",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        resourceId = row[0]
        resourceName = row[1]
        tierName = get_tier_by_resource_name(ctx, resourceName)
        resourceList.append({'name': resourceName,
                             'id': resourceId,
                             'tier': tierName})

    return resourceList


@api.make()
def api_uu_resource_monthly_stats(ctx):
    """Collect storage data for all categories."""
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    categories = getCategories(ctx)

    return getMonthlyCategoryStorageStatistics(categories, ctx)


@api.make()
def api_uu_resource_monthly_stats_dm(ctx):
    """Collect storage data for a datamanager."""
    datamanager = user.full_name(ctx)
    categories = getCategoriesDatamanager(datamanager, ctx)

    return getMonthlyCategoryStorageStatistics(categories, ctx)


@api.make()
def api_uu_resource_groups_dm(ctx):
    """Get all groups for all categories a person is datamanager of."""
    datamanager = user.full_name(ctx)
    categories = getCategoriesDatamanager(datamanager, ctx)

    all_group = []
    return getGroupsOnCategories(categories, ctx)


@api.make()
def api_uu_resource_monthly_category_stats_export_dm(ctx):
    """
    Collect storage stats for all twelve months based upon categories a user is datamanager of.

    Statistics gathered:
    - Category
    - Subcategory
    - Groupname
    - Tier
    - 12 columns, one per month, with used storage count in bytes
    """
    datamanager = user.full_name(ctx)
    categories = getCategoriesDatamanager(datamanager, ctx)
    allStorage = []

    # Select a full year by not limiting constants.UUMETADATASTORAGEMONTH to a perticular month. But only on its presence.
    # There always is a maximum of one year of history of storage data
    for category in categories:
        groupToSubcategory = {}

        iter = genquery.row_iterator(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category + "\",%' AND META_USER_ATTR_NAME like  '" + constants.UUMETADATASTORAGEMONTH + "%'",
            genquery.AS_LIST, ctx
        )

        for row in iter:
            attrValue = row[0]
            month = row[1]
            month = str(int(month[-2:]))  # the month storage data is about, is taken from the attr_name of the AVU
            groupName = row[3]

            # Determine subcategory on groupName
            try:
                subcategory = groupToSubcategory[groupName]
            except KeyError:
                catInfo = groupGetCategoryInfo(groupName, ctx)
                subcategory = catInfo['subcategory']
                groupToSubcategory[groupName] = subcategory

            temp = jsonutil.parse(attrValue)
            category = temp[0]
            tier = temp[1]
            storage = int(float(temp[2]))

            allStorage.append({'category': category,
                               'subcategory': subcategory,
                               'groupname': groupName,
                               'tier': tier,
                               'month': month,
                               'storage': str(storage)})

    return allStorage


def groupGetCategoryInfo(groupName, callback):
    """
    Get category and subcategory for a group.

    Returns a dict with indices 'category' and 'subcategory'.
    """
    category = ''
    subcategory = ''

    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + groupName + "' AND  META_USER_ATTR_NAME LIKE '%category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        attrName = row[0]
        attrValue = row[1]

        if attrName == 'category':
            category = attrValue
        elif attrName == 'subcategory':
            subcategory = attrValue

    return {'category': category, 'subcategory': subcategory}


def getMonthlyCategoryStorageStatistics(categories, callback):
    """
    Collect storage stats of last month only.

    Storage is summed up for each category/tier combination.
    Example: Array ( [0] => Array ( [category] => initial [tier] => Standard [storage] => 15777136 )
    """
    month = '%0*d' % (2, datetime.now().month)
    metadataName = constants.UUMETADATASTORAGEMONTH + month
    storageDict = {}

    for category in categories:
        iter = genquery.row_iterator(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category + "\",%' AND META_USER_ATTR_NAME = '" + metadataName + "'",
            genquery.AS_LIST, callback
        )

        for row in iter:
            # hier wordt door alle groepen gezocht, geordend van een category.
            # per tier moet worden gesommeerd om totale hoeveelheid storage op een tier te verkrijgen.
            attrValue = row[0]

            temp = jsonutil.parse(attrValue)
            category = temp[0]
            tier = temp[1]
            storage = int(float(temp[2]))

            try:
                storageDict[category][tier] = storageDict[category][tier] + storage
            except KeyError:
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

    return allStorage


def getGroupsOnCategories(categories, callback):
    """Get all groups belonging to all given categories."""
    groups = []
    metadataAttrNameRefMonth = constants.UUMETADATASTORAGEMONTH + '%0*d' % (2, datetime.now().month)

    for category in categories:
        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, callback
        )

        for row in iter:
            groupName = row[0]
            if groupName.startswith('research-'):
                iter2 = genquery.row_iterator(
                    "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
                    "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + groupName + "'",
                    genquery.AS_LIST, callback
                )

                data_size = 0
                for row in iter2:
                    data = row[0]
                    temp = jsonutil.parse(data)
                    data_size = data_size + int(temp[2])  # no construction for summation required in this case
                groups.append([groupName, data_size])

    return groups


def getCategoriesDatamanager(datamanagerName, callback):
    """Get all categories for current datamanager."""
    categories = []

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        # @TODO membership still has to be checked
        datamanagerGroupname = row[0]
        temp = datamanagerGroupname.split('-')  # 'datamanager-initial' is groupname of datamanager, second part is category
        categories.append(temp[1])

    return categories


def getCategories(callback):
    """Get all categories currently present."""
    categories = []

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND  META_USER_ATTR_NAME  = 'category'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        categories.append(row[0])

    return categories


def get_tier_by_resource_name(ctx, res_name):
    """
    Get Tiername, if present, for given resource.

    If not present, fall back to default tier name.
    """
    tier = constants.UUDEFAULTRESOURCETIER  # Add default tier as this might not be present in database.

    # find (possibly present) tier for this resource
    iter = genquery.row_iterator(
        "RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE",
        "RESC_NAME = '{}' AND META_RESC_ATTR_NAME = '{}'"
        .format(res_name, constants.UURESOURCETIERATTRNAME),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        tier = row[3]

    return tier
