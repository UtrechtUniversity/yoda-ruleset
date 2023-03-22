# -*- coding: utf-8 -*-
"""Functions for statistics module."""

__copyright__ = 'Copyright (c) 2018-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

import genquery

import groups
from util import *

__all__ = ['api_resource_browse_group_data',
           'api_resource_monthly_category_stats',
           'api_resource_category_stats',
           'api_resource_full_year_differentiated_group_storage',
           'rule_resource_store_monthly_storage_statistics',
           'rule_resource_transform_old_storage_data',
           'rule_resource_research',
           'rule_resource_vault']


@api.make()
def api_resource_browse_group_data(ctx,
                                   sort_on='name',
                                   sort_order='asc',
                                   offset=0,
                                   limit=10,
                                   search_groups=""):
    """Get paginated group data groupname / size

    :param ctx:        Combined type of a callback and rei struct
    :param sort_on:    Column to sort on ('name', 'modified' or size)
    :param sort_order: Column sort order ('asc' or 'desc')
    :param offset:     Offset to start browsing from
    :param limit:      Limit number of results
    :param search_groups: Search specific groups

    :returns: Dict with paginated collection contents
    """
    user_name = user.name(ctx)
    user_zone = user.zone(ctx)

    search_sql = ""
    if search_groups:
        # The maximum allowed number of characters in the group name is 63.
        search_sql = "AND USER_GROUP_NAME like '%%{}%%' ".format(search_groups[:63])

    if user.is_admin(ctx):
        groups_research = [a for a
                           in genquery.Query(ctx, "USER_GROUP_NAME",
                                             "USER_GROUP_NAME like 'research-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_deposit = [a for a
                          in genquery.Query(ctx, "USER_GROUP_NAME",
                                            "USER_GROUP_NAME like 'deposit-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_intake = [a for a
                          in genquery.Query(ctx, "USER_GROUP_NAME",
                                            "USER_GROUP_NAME like 'intake-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_grp = [a for a
                          in genquery.Query(ctx, "USER_GROUP_NAME",
                                            "USER_GROUP_NAME like 'grp-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_datarequest = [a for a
                          in genquery.Query(ctx, "USER_GROUP_NAME",
                                            "USER_GROUP_NAME like 'datarequest-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups = list(set(groups_research + groups_deposit + groups_intake + groups_grp + groups_datarequest))
    else:
        categories = get_categories(ctx)
        groups_dm = get_groups_on_categories(ctx, categories, search_groups)

        groups_research_member = [a for a
                                  in genquery.Query(ctx, "USER_GROUP_NAME",
                                                    "USER_GROUP_NAME like 'research-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_deposit_member = [a for a
                                 in genquery.Query(ctx, "USER_GROUP_NAME",
                                                   "USER_GROUP_NAME like 'deposit-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_intake_member = [a for a
                                  in genquery.Query(ctx, "USER_GROUP_NAME",
                                                    "USER_GROUP_NAME like 'intake-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_grp_member = [a for a
                                 in genquery.Query(ctx, "USER_GROUP_NAME",
                                                   "USER_GROUP_NAME like 'grp-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_datarequest_member = [a for a
                                  in genquery.Query(ctx, "USER_GROUP_NAME",
                                                    "USER_GROUP_NAME like 'datarequest-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups = list(set(groups_research_member + groups_deposit_member + groups_intake_member + groups_grp_member + groups_datarequest_member + groups_dm))

    # groups.sort()
    group_list = []
    for groupname in groups:
        data_size = get_group_data_sizes(ctx, groupname)
        group_list.append([groupname, data_size])

    # Sort the list as requested by user
    sort_key = 0
    if sort_on == 'size':
        sort_key = 1
    sort_reverse = False
    if sort_order == 'desc':
        sort_reverse = True
    group_list.sort(key=lambda x: x[sort_key], reverse=sort_reverse)

    # Only at this point we have the list in correct shape/order and can the limit and offset be applied
    # Format for datatables in frontend throughout yoda
    group_list_sorted = []
    group_slice = group_list[offset: offset + limit]

    for group_data in group_slice:
        members = group.members(ctx, group_data[0])
        group_list_sorted.append({"name": group_data[0], "size": group_data[1], "member_count": len(list(members))})

    return {'total': len(group_list), 'items': group_list_sorted}


@rule.make()
def rule_resource_transform_old_storage_data(ctx):
    """ Transform all old school storage data collection to the new way.
    Get rid of tiers.
    Fact: only one tier was used in all yoda instances

    [cat, research, vault, revisions, total]

    :param ctx:           Combined type of a callback and rei struct

    :returns: API status
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Step through all aggregated storage data that was previously recorded monthly
    # PRECONDITION: only 1 tier is used throughout the entire use of the previously used collection method.

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_NAME, USER_GROUP_NAME",
        "META_USER_ATTR_NAME like '{}%%'".format(constants.UUMETADATASTORAGEMONTH),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # group - [category, tier, total]
        # group - [category, research, vault, revisions, total]

        # As only one tier was used, each found total for a group, can directly be set as the total for that group.
        # No differentation into research / vault / revisions as this information is not present.

        storage_data = jsonutil.parse(row[0])
        storage_category = storage_data[0]
        storage_total = int(storage_data[2])
        storage_month = int(row[1][-2:])
        storage_group = row[3]

        if storage_month != current_month:
            # Only do the transformation when NOT in current month itself.
            storage_year = current_year if storage_month <= current_month else current_year - 1

            # set the measurement date on the 15th of any month
            storage_attr_name = constants.UUMETADATAGROUPSTORAGETOTALS + "{}_{}_17".format(storage_year, '%0*d' % (2, storage_month))
            storage_attr_val = '["{}", 0, 0, 0, {}]'.format(storage_category, storage_total)

            # First test if exists - if so => delete:
            # First delete possibly previously stored data
            iter2 = genquery.row_iterator(
                "META_USER_ATTR_VALUE, META_USER_ATTR_NAME, USER_GROUP_NAME",
                "META_USER_ATTR_NAME = '{}' AND META_USER_ATTR_VALUE = '{}' AND USER_GROUP_NAME = '{}'".format(storage_attr_name, storage_attr_val, storage_group),
                genquery.AS_LIST, ctx
            )
            for row2 in iter2:
                avu.rm_from_group(ctx, storage_group, storage_attr_name, storage_attr_val)

            # Add data in new manner without tiers
            avu.associate_to_group(ctx, storage_group, storage_attr_name, storage_attr_val)

            # ?? Do we delete previously stored monthly totals??
            # avu.rm_from_group(ctx, row[3], row[1], row[0])

    return 'ok'


@api.make()
def api_resource_full_year_differentiated_group_storage(ctx, group_name):
    # def api_resource_full_range ...

    """Return the full range of registered storage data differentiated into vault/research/revision/total

    :param ctx:           Combined type of a callback and rei struct
    :param group_name:    Group that is searched for storage data

    :returns: API status
    """
    # Check permissions for this function
    # Member of this group?
    member_type = groups.user_role(ctx, group_name, user.full_name(ctx))
    if member_type not in ['reader', 'normal', 'manager']:
        category = groups.group_category(ctx, group_name)
        if not groups.user_is_datamanager(ctx, category, user.full_name(ctx)):
            if user.user_type(ctx) != 'rodsadmin':
                return api.Error('not_allowed', 'Insufficient permissions')

    labels = []
    research = []
    vault = []
    revision = []
    iter = genquery.row_iterator(
        "ORDER(META_USER_ATTR_NAME), META_USER_ATTR_VALUE",
        "USER_NAME = '{}' AND META_USER_ATTR_NAME like '{}%%' AND USER_TYPE = 'rodsgroup'".format(group_name, constants.UUMETADATAGROUPSTORAGETOTALS),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # 2022_01_15
        storage_date = row[0][-10:].replace('_', '-')
        labels.append(storage_date)

        # Make compatible with json strings containing ' coming from previous erroneous storage conversion
        # [category, research, vault, revision, total]
        temp = jsonutil.parse(row[1].replace("'", '"'))
        research.append(temp[1])
        vault.append(temp[2])
        revision.append(temp[3])

    # example: {'labels': ['2022-06-01', '2022-06-02', '2022-06-03'], 'research': [123, 456, 789], 'vault': [666, 777, 888], 'revision': [200, 300, 400]}
    return {'labels': labels, 'research': research, 'vault': vault, 'revision': revision}


@api.make()
def api_resource_category_stats(ctx):
    """Collect storage stats of last month for categories.
    Storage is summed up for each category.

    :param ctx:      Combined type of a callback and rei struct

    :returns: Storage stats of last month for a list of categories
    """

    categories = get_categories(ctx)

    storage = {}

    # Go through current groups of current categories.
    # This function has no historic value so it is allowed to do so
    for category in categories:
        storage[category] = {'total': 0, 'research': 0, 'vault': 0, 'revision': 0}

        # for all groups in category
        groups = get_groups_on_categories(ctx, [category])
        for group in groups:
            if group.startswith(('research', 'deposit', 'intake', 'grp', 'datarequest')):
                # Only check the most recent storage measurement
                iter = list(genquery.Query(ctx,
                            ['META_USER_ATTR_VALUE', 'ORDER_DESC(META_USER_ATTR_NAME)', 'USER_NAME', 'USER_GROUP_NAME'],
                            "META_USER_ATTR_VALUE like '[\"{}\",%%' AND META_USER_ATTR_NAME like '{}%%' AND USER_NAME = '{}'".format(category, constants.UUMETADATAGROUPSTORAGETOTALS, group),
                            offset=0, limit=1, output=genquery.AS_LIST))

                for row in iter:
                    temp = jsonutil.parse(row[0])

                    storage[category]['total'] += temp[4]
                    storage[category]['research'] += temp[1]
                    storage[category]['vault'] += temp[2]
                    storage[category]['revision'] += temp[3]

    # Now go through all totals
    all_storage = []
    for category in categories:
        storage_humanized = {}
        # humanize storage sizes for the frontend
        for type in ['total', 'research', 'vault', 'revision']:
            storage_humanized[type] = misc.human_readable_size(1.0 * storage[category][type])

        all_storage.append({'category': category,
                           'storage': storage_humanized})

    return sorted(all_storage, key=lambda d: d['category'])


@api.make()
def api_resource_monthly_category_stats(ctx):
    """Collect storage stats for all twelve months based upon categories a user is datamanager of.

    Statistics gathered:
    - Category
    - Subcategory
    - Groupname
    - n columns - one per month, with used storage count in bytes

    :param ctx:  Combined type of a callback and rei struct

    :returns: API status
    """
    current_month = datetime.now().month
    current_year = datetime.now().year

    # find minimal registered date registered.
    iter = list(genquery.Query(ctx, ['ORDER(META_USER_ATTR_NAME)'],
                               "META_USER_ATTR_NAME like '{}%%'".format(constants.UUMETADATAGROUPSTORAGETOTALS),
                               offset=0, limit=1, output=genquery.AS_LIST))

    for row in iter:
        min_year = int(row[0][-10:-6])
        min_month = int(row[0][-5:-3])

    # Prepare storage data
    # Create dict with all groups that will contain list of storage values corresponding to complete range from minimal date till now.
    group_storage = {}

    # All storage periods (yyyy-mm) for frontend
    storage_dates = []

    # A group always has 1 distinct category and 1 distinct subcateory
    group_catdata = {}

    # Initialisation
    categories = get_categories(ctx)
    for category in categories:
        # for all groups in category
        groups = get_groups_on_categories(ctx, [category])
        for group in groups:
            if group.startswith(('research', 'deposit', 'intake', 'grp', 'datarequest')):
                group_storage[group] = []
                group_catdata[group] = {'category': category,
                                        'subcategory': get_group_category_info(ctx, group)['subcategory']}

    # Loop from earliest data to now and find storage for each group/date combination
    while min_month != current_month or min_year != current_year:
        date_reference = "{}_{}".format(min_year, '%0*d' % (2, min_month))
        storage_dates.append(date_reference)

        for category in categories:
            # for all groups in category
            groups = get_groups_on_categories(ctx, [category])
            for group in groups:
                if group.startswith(('research', 'deposit', 'intake', 'grp', 'datarequest')):
                    storage = get_group_data_sizes(ctx, group, date_reference)
                    group_storage[group].append(storage[3])

        # Next time period based on month
        min_month += 1
        if min_month > 12:
            min_month = 1
            min_year += 1

    date_reference = "{}_{}".format(min_year, '%0*d' % (2, min_month))
    storage_dates.append(date_reference)

    for category in categories:
        # for all groups in category
        groups = get_groups_on_categories(ctx, [category])
        for group in groups:
            if group.startswith(('research', 'deposit', 'intake', 'grp', 'datarequest')):
                storage = get_group_data_sizes(ctx, group, date_reference)
                group_storage[group].append(storage[3])

    all_storage = []
    for group in group_storage:
        all_storage.append({'category': group_catdata[group]['category'],
                            'subcategory': group_catdata[group]['subcategory'],
                            'groupname': group,
                            'storage': group_storage[group]})

    return {'storage': all_storage, 'dates': storage_dates}


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


def get_groups_on_categories(ctx, categories, search_groups=""):
    """Get all groups belonging to all given categories.

    :param ctx:           Combined type of a callback and rei struct
    :param categories:    List of categories groups have to be found for
    :param search_groups: Find specific groups

    :returns: All groups belonging to all given categories
    """
    groups = []

    search_sql = ""
    if search_groups:
        search_sql = "AND USER_GROUP_NAME like '%%{}%%' ".format(search_groups)

    for category in categories:
        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'research-%%' " + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)

        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'deposit-%%' " + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)
        
        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'intake-%%' " + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)

        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'grp-%%' " + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)
        
        iter = genquery.row_iterator(
            "USER_NAME",
            "USER_GROUP_NAME like 'datarequest-%%' " + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)
        

    return groups


@rule.make()
def rule_resource_store_monthly_storage_statistics(ctx):
    # @rule.make()
    # def rule_resource_store_group_storage_statistics(ctx):
    """
    !!! Function has to be renamed as name does not correspond to its actual function


    For all categories present, store all found storage data for each group belonging to these categories.

    Store as metadata on group level as [category, research, vault, revision, total]

    :param ctx:  Combined type of a callback and rei struct

    :returns: Storage data for each group of each category
    """
    zone = user.zone(ctx)

    dt = datetime.today()
    md_storage_date = constants.UUMETADATAGROUPSTORAGETOTALS + dt.strftime("%Y_%m_%d")

    # Delete previous data for this perticular day if present at all
    # Each group should only have one aggrageted totals attribute per day
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE, USER_GROUP_NAME",
        "META_USER_ATTR_NAME = '" + md_storage_date + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        avu.rm_from_group(ctx, row[1], md_storage_date, row[0])

    # Get all categories
    categories = []
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        categories.append(row[0])

    # Steps to be taken per group
    # The software distinguishes 2 separate areas.
    # 1) VAULT AREA
    # 2) RESEARCH AREA - which includes research and deposit groups
    # 3) REVISION AREA
    steps = ['research', 'vault']
    total = {'research': 0, 'vault': 0, 'revision': 0}

    # Loop through all categories
    for category in categories:
        groups = get_groups_on_category(ctx, category)

        for group in groups:
            # COLLECT GROUP DATA
            # Per group collect totals for vault, research and revision
            # Look at research, deposit, intake, grp and datarequest groups
            if group.startswith(('research', 'deposit', 'intake', 'grp', 'datarequest')):
                # RESEARCH AND VAULT SPACE
                for step in steps:
                    total[step] = 0

                    if step == 'research':
                        path = '/' + zone + '/home/' + group
                    else:
                        # groupname can start with 'research-' or 'deposit-'
                        if group.startswith('research-'):
                            vault_group = group.replace('research-', 'vault-', 1)
                        else:
                            vault_group = group.replace('deposit-', 'vault-', 1)
                        path = '/' + zone + '/home/' + vault_group

                    # Per group two statements are required to gather all data
                    # 1) data in folder itself
                    # 2) data in all subfolders of the folder

                    for folder in ['self', 'subfolders']:
                        if folder == 'self':
                            whereClause = "COLL_NAME = '" + path + "'"
                        else:
                            whereClause = "COLL_NAME like '" + path + "/%'"

                        iter = genquery.row_iterator(
                            "SUM(DATA_SIZE)",
                            whereClause,
                            genquery.AS_LIST, ctx
                        )

                        for row in iter:
                            if row[0] != '':
                                total[step] += int(row[0])

                # REVISION SPACE
                total['revision'] = 0
                revision_path = '/{}{}/{}'.format(zone, constants.UUREVISIONCOLLECTION, group)
                whereClause = "COLL_NAME like '" + revision_path + "/%'"
                iter = genquery.row_iterator(
                    "SUM(DATA_SIZE)",
                    whereClause,
                    genquery.AS_LIST, ctx
                )
                for row in iter:
                    if row[0] != '':
                        total['revision'] += int(row[0])

                # For intake, grp and datarequest groups
                total['other'] = 0
                group_path = '/' + zone + '/home/' + group
                
                for folder in ['self', 'subfolders']:
                    if folder == 'self':
                        whereClause = "COLL_NAME = '" + group_path + "'"
                    else:
                        whereClause = "COLL_NAME like '" + group_path + "/%'"

                iter = genquery.row_iterator(
                    "SUM(DATA_SIZE)",
                    whereClause,
                    genquery.AS_LIST, ctx
                )
                for row in iter:
                    if row[0] != '':
                        total['other'] += int(row[0])

                # STORE GROUP DATA
                # STORAGE_TOTAL_REVISION_2023_01_09
                # constructed this way to be backwards compatible (not using json.dump)

                # [category, research, vault, revision, total]
                storage_total = total['research'] + total['vault'] + total['revision']
                
                storage_val = "[\"{}\", {}, {}, {}, {}]".format(category, total['research'], total['vault'], total['revision'], storage_total)
                storage_val_other = "[\"{}\", {}, {}, {}, {}]".format(category, 0, 0, 0, total['other'])

                # Only store if storage_total>0???
                # Sla maar wel op want anders niet duidelijk of het gebeurd is

                # write as metadata (kv-pair) to current group
                if group.startswith(('research', 'deposit')):
                    log.write(ctx, 'In first if')
                    log.write(ctx,group)
                    log.write(ctx,storage_val)
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val)
                if group.startswith(('intake', 'grp', 'datarequest')):
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val_other)

                log.write(ctx, 'Research, Vault and Revision data collected and stored for current month')
            else:  # except Exception:
                log.write(ctx, 'SKIPPING GROUP AS NOT prefixed with either research-, deposit-, intake-, grp- or datarequest-')
                log.write(ctx, group)
    return 'ok'


def get_categories(ctx):
    """Get all categories for current user.

    :param ctx: Combined type of a callback and rei struct

    :returns: All categories for current user
    """
    categories = []

    if user.is_admin(ctx):
        iter = genquery.row_iterator(
            "META_USER_ATTR_VALUE",
            "USER_TYPE = 'rodsgroup' AND  META_USER_ATTR_NAME  = 'category'",
            genquery.AS_LIST, ctx
        )

        for row in iter:
            categories.append(row[0])
    else:
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


def get_group_data_sizes(ctx, group_name, ref_period=None):
    """Get group data sizes and return as a list of values.

    If no reference period is specified return closest to today.

    :param ctx:        Combined type of a callback and rei struct
    :param group_name: Name of group to get data sizes of
    :param ref_period: Reference period written as 'YYYY-MM'

    :returns: List with group data sizes, [research_storage, vault_storage, revision_storage, total_storage]
    """
    # Get most recent information present for this group
    if ref_period:
        md_storage_period = constants.UUMETADATAGROUPSTORAGETOTALS + ref_period
    else:
        md_storage_period = constants.UUMETADATAGROUPSTORAGETOTALS

    iter = genquery.Query(ctx,
                          ['META_USER_ATTR_VALUE', 'ORDER_DESC(META_USER_ATTR_NAME)', 'USER_NAME', 'USER_GROUP_NAME'],
                          "META_USER_ATTR_NAME like '" + md_storage_period + "%%' AND USER_NAME = '" + group_name + "'",
                          offset=0, limit=1, output=genquery.AS_LIST)

    for row in list(iter):
        # the replace is merely here due to earlier (erroneous0 values that were added as '' in json where this should have been ""
        temp = jsonutil.parse(row[0].replace("'", '"'))
        # [research_storage, vault_storage, revision_storage, total_storage]
        return [int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4])]

    return [0, 0, 0, 0]


def rule_resource_research(rule_args, callback, rei):
    rule_args[0] = config.resource_research


def rule_resource_vault(rule_args, callback, rei):
    rule_args[0] = config.resource_vault
