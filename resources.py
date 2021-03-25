# -*- coding: utf-8 -*-
"""Functions for statistics module."""

__copyright__ = 'Copyright (c) 2018-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

import meta_form
from util import *
from util.query import Query

__all__ = ['api_resource_list_groups',
           'api_resource_monthly_stats_dm',
           'api_resource_monthly_category_stats_export_dm',
           'api_resource_monthly_stats',
           'api_resource_resource_and_tier_data',
           'api_resource_tier',
           'api_resource_get_tiers',
           'api_resource_save_tier',
           'api_resource_user_is_datamanager',
           'api_resource_full_year_group_data',
           'rule_resource_store_monthly_storage_statistics']


@api.make()
def api_resource_save_tier(ctx, resource_name, tier_name):
    """Save tier for given resource as metadata.

    :param ctx:           Combined type of a callback and rei struct
    :param resource_name: Resource that the tier is equipped with
    :param tier_name:     Name of the tier that is given to the resource

    :returns: API status
    """
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    if not resource_exists(ctx, resource_name):
        return api.Error('not_exists', 'Given resource name is not in use')

    meta_attr_name = constants.UURESOURCETIERATTRNAME

    avu.set_on_resource(ctx, resource_name, meta_attr_name, tier_name)


@api.make()
def api_resource_full_year_group_data(ctx, group_name):
    """Get a full year of monthly storage data starting from current month and look back one year.

    :param ctx:           Combined type of a callback and rei struct
    :param group_name:    group that is searched for storage data

    :returns: API status
    """

    # Check permissions for this function
    # Member of this group?
    member_type = meta_form.user_member_type(ctx, group_name, user.full_name(ctx))
    if member_type not in ['reader', 'normal', 'manager']:
        category = meta_form.group_category(ctx, group_name)
        if not meta_form.user_is_datamanager(ctx, category, user.full_name(ctx)):
            if user.user_type(ctx) != 'rodsadmin':
                return api.Error('not_allowed', 'Insufficient permissions')

    current_month = '%0*d' % (2, datetime.now().month)
    full_year_data = {}  # all tiers with storage size per month
    total_storage = 0

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
            data_size = data[2]
            total_storage += data_size
            try:
                full_year_data[tierName][referenceMonth] = data_size
            except KeyError:
                full_year_data[tierName] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                full_year_data[tierName][referenceMonth] = data_size

    # Supporting info for the frontend.
    months_order = []
    for i in [range(1, 13)]:
        storage_month = current_month - i
        # reverse the order of months
        # months_order[11 - i] = 10 if storage_month + 12 < 1 else storage_month

    return {'tiers': full_year_data, 'months': months_order, 'total_storage': total_storage}


@api.make()
def api_resource_list_groups(ctx):
    """Get the research groups a user is member or datamanager of."""
    user_name = user.name(ctx)
    user_zone = user.zone(ctx)

    categories = get_categories_datamanager(ctx)
    groups_dm = get_groups_on_categories(ctx, categories)

    groups_member = [a for a
                     in Query(ctx, "USER_GROUP_NAME",
                                   "USER_GROUP_NAME like 'research-%%' AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]

    groups = list(set(groups_member + groups_dm))
    groups.sort()

    group_list = []
    for group in groups:
        data_size = get_group_data_size(ctx, group)
        group_list.append((group, misc.human_readable_size(data_size)))

    return group_list


@api.make()
def api_resource_user_is_datamanager(ctx):
    """Check whether current user is datamanager of group."""
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
def api_resource_get_tiers(ctx):
    """As rodsadmin get all tiers present."""
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    return get_all_tiers(ctx)


@api.make()
def api_resource_tier(ctx, res_name):
    """Get the tier belonging to the given resource.

    :param ctx:      Combined type of a callback and rei struct
    :param res_name: Resource that the tier is equipped with

    :returns: API status
    """
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    return get_tier_by_resource_name(ctx, res_name)


@api.make()
def api_resource_resource_and_tier_data(ctx):
    """List al resources and its tier data."""
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
def api_resource_monthly_stats(ctx):
    """As rodsadmin collect monthly statistics"""
    if user.user_type(ctx) != 'rodsadmin':
        return api.Error('not_allowed', 'Insufficient permissions')

    categories = get_categories(ctx)

    return getMonthlyCategoryStorageStatistics(ctx, categories)


@api.make()
def api_resource_monthly_stats_dm(ctx):
    """Collect storage data for a datamanager."""
    categories = get_categories_datamanager(ctx)

    return getMonthlyCategoryStorageStatistics(ctx, categories)


@api.make()
def api_resource_monthly_category_stats_export_dm(ctx):
    """Collect storage stats for all twelve months based upon categories a user is datamanager of.

    Statistics gathered:
    - Category
    - Subcategory
    - Groupname
    - Tier
    - 12 columns, one per month, with used storage count in bytes

    :param ctx:  Combined type of a callback and rei struct

    :returns: API status
    """
    categories = get_categories_datamanager(ctx)
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
                catInfo = get_group_category_info(ctx, groupName)
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


def get_group_category_info(ctx, groupName):
    """Get category and subcategory for a group.

    :param ctx:       Combined type of a callback and rei struct
    :param groupName: groupname to get cat/subcat info for

    :returns: A dict with indices 'category' and 'subcategory'.
    """
    category = ''
    subcategory = ''

    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + groupName + "' AND  META_USER_ATTR_NAME LIKE '%category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        attrName = row[0]
        attrValue = row[1]

        if attrName == 'category':
            category = attrValue
        elif attrName == 'subcategory':
            subcategory = attrValue

    return {'category': category, 'subcategory': subcategory}


def getMonthlyCategoryStorageStatistics(ctx, categories):
    """Collect storage stats of last month for a list of categories.

    Storage is summed up for each category/tier combination.
    Example: Array ( [0] => Array ( [category] => initial [tier] => Standard [storage] => 15777136 )

    :param ctx:        Combined type of a callback and rei struct
    :param categories: List of categories to collect storage data for

    :returns: Storage stats of last month for a list of categories
    """
    month = '%0*d' % (2, datetime.now().month)
    metadataName = constants.UUMETADATASTORAGEMONTH + month

    storageDict = {}

    for category in categories:
        iter = genquery.row_iterator(
            "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
            "META_USER_ATTR_VALUE like '[\"" + category + "\",%' AND META_USER_ATTR_NAME = '" + metadataName + "'",
            genquery.AS_LIST, ctx
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


def get_groups_on_categories(ctx, categories):
    """Get all groups belonging to all given categories.

    :param ctx:        Combined type of a callback and rei struct
    :param categories: List of categories groups have to be found for

    :returns: All groups belonging to all given categories
    """
    groups = []

    for category in categories:
        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'research-%%' AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )

        for row in iter:
            groupName = row[0]
            groups.append(groupName)

    return groups


def get_categories_datamanager(ctx):
    """Get all categories for current datamanager.

    :param ctx: Combined type of a callback and rei struct

    :returns: All categories for current datamanager
    """
    categories = []

    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' AND USER_NAME like 'datamanager-%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        datamanagerGroupname = row[0]

        if user.is_member_of(ctx, datamanagerGroupname):
            # Example: 'datamanager-initial' is groupname of datamanager, second part is category
            temp = '-'.join(datamanagerGroupname.split('-')[1:])
            categories.append(temp)

    return categories


def get_tier_by_resource_name(ctx, res_name):
    """Get Tiername, if present, for given resource.

    If not present, fall back to default tier name.

    :param ctx:      Combined type of a callback and rei struct
    :param res_name: Name of the resource to get the tier name for

    :returns: Tiername for given resource
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


@rule.make()
def rule_resource_store_monthly_storage_statistics(ctx):
    """For all categories known store all found storage data for each group belonging to those category.

    Store as metadata on group level holding
    1) category of group on probe date - this can change
    2) tier
    3) actual calculated storage for the group

    :param ctx:  Combined type of a callback and rei struct

    :returns: Storage data for each group of each category
    """
    zone = user.zone(ctx)

    # Get storage month with leading 0
    dt = datetime.today()
    md_storage_month = constants.UUMETADATASTORAGEMONTH + dt.strftime("%m")

    # Delete previous data for that month. Could be one year ago as this is circular buffer containing max 1 year
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE, USER_GROUP_NAME",
        "META_USER_ATTR_NAME = '" + md_storage_month + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        avu.rm_from_group(ctx, row[1], md_storage_month, row[0])

    # Get all categories
    categories = []
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        categories.append(row[0])

    # Get all tiers - Standard must be present
    tiers = get_all_tiers(ctx)

    # List of resources and their corresponding tiers (for easy access further)
    resource_tiers = {}
    for resource in get_resources(ctx):
        resource_tiers[resource] = get_tier_by_resource_name(ctx, resource)

    # Steps to be taken per group
    steps = ['research', 'vault']

    # Loop through all categories
    for category in categories:
        groups = get_groups_on_category(ctx, category)

        for group in groups:
            # Per group collect totals for category and tier

            # Loop though all tiers and set storage to 0
            tier_storage = {}
            for tier in tiers:
                tier_storage[tier] = 0

            # per group handle research and vault
            for step in steps:
                if step == 'research':
                    path = '/' + zone + '/home/' + group
                else:
                    path = '/' + zone + '/home/vault/' + group.replace('research-', 'vault-', 1)

                # Per group two statements are required to gather all data
                # 1) data in folder itself
                # 2) data in all subfolders of the folder

                for folder in ['self', 'subfolders']:
                    if folder == 'self':
                        whereClause = "COLL_NAME = '" + path + "'"
                    else:
                        whereClause = "COLL_NAME like '" + path + "%'"

                    iter = genquery.row_iterator(
                        "SUM(DATA_SIZE), RESC_NAME",
                        whereClause,
                        genquery.AS_LIST, ctx
                    )

                    for row in iter:
                        # sum up for this tier
                        the_tier = resource_tiers[row[1]]
                        tier_storage[the_tier] += int(row[0])

            # 3) Revision erea
            revision_path = '/' + zone + '/' + constants.UUREVISIONCOLLECTION + '/' + group
            whereClause = "COLL_NAME like '" + revision_path + "%'"
            iter = genquery.row_iterator(
                "SUM(DATA_SIZE), RESC_NAME",
                whereClause,
                genquery.AS_LIST, ctx
            )
            for row in iter:
                # sum up for this tier
                the_tier = resource_tiers[row[1]]
                tier_storage[the_tier] += int(row[0])

            # Write total storages as metadata on current group for any tier
            key = md_storage_month
            # val = [category, tier, storage]
            for tier in tiers:
                # constructed this way to be backwards compatible (not using json.dump)
                val = "[\"" + category + "\", \"" + tier + "\", " + str(tier_storage[tier]) + "]"
                # write as metadata (kv-pair) to current group
                avu.associate_to_group(ctx, group, key, val)

    return 'ok'


def resource_exists(ctx, resource_name):
    """Check whether given resource actually exists."""
    iter = genquery.row_iterator(
        "RESC_ID, RESC_NAME",
        "RESC_NAME = '{}'"
        .format(resource_name),
        genquery.AS_LIST, ctx
    )

    for _row in iter:
        return True

    return False


def get_all_tiers(ctx):
    """List all tiers currently present including 'Standard'."""
    tiers = [constants.UUDEFAULTRESOURCETIER]

    iter = genquery.row_iterator(
        "META_RESC_ATTR_VALUE",
        "META_RESC_ATTR_NAME = '" + constants.UURESOURCETIERATTRNAME + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        if not row[0] == constants.UUDEFAULTRESOURCETIER:
            if row[0] not in tiers:
                tiers.append(row[0])

    return tiers


def get_categories(ctx):
    """Get all categories currently present."""
    categories = []

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND  META_USER_ATTR_NAME  = 'category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        categories.append(row[0])

    return categories


def get_groups_on_category(ctx, category):
    """Get all groups for category."""
    groups = []
    iter = genquery.row_iterator(
        "USER_NAME",
        "USER_TYPE = 'rodsgroup' "
        "AND  META_USER_ATTR_NAME  = 'category' "
        "AND  META_USER_ATTR_VALUE = '" + category + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        groups.append(row[0])

    return groups


def get_resources(ctx):
    """Get all resources."""
    resources = []
    iter = genquery.row_iterator(
        "RESC_NAME",
        "",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        resources.append(row[0])

    return resources


def get_group_data_size(ctx, group_name):
    metadataAttrNameRefMonth = constants.UUMETADATASTORAGEMONTH + '%0*d' % (2, datetime.now().month)

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME",
        "META_USER_ATTR_NAME = '" + metadataAttrNameRefMonth + "' AND USER_NAME = '" + group_name + "'",
        genquery.AS_LIST, ctx
    )

    data_size = 0
    for row in iter:
        data = row[0]
        temp = jsonutil.parse(data)
        data_size = data_size + int(float(temp[2]))  # no construction for summation required in this case

    return data_size
