# -*- coding: utf-8 -*-
"""Functions for statistics module."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

import genquery

import groups
from util import *

__all__ = ['api_resource_browse_group_data',
           'api_resource_monthly_category_stats',
           'api_resource_category_stats',
           'api_resource_full_year_differentiated_group_storage',
           'rule_resource_store_storage_statistics',
           'rule_resource_research',
           'rule_resource_update_resc_arb_data',
           'rule_resource_update_misc_arb_data',
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
        groups_research = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'research-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_deposit = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'deposit-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_intake = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'intake-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups_grp = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'grp-%%' " + search_sql + "AND USER_ZONE = '{}'".format(user_zone))]
        groups = list(set(groups_research + groups_deposit + groups_intake + groups_grp))
    else:
        categories = get_categories(ctx)
        groups_dm = get_groups_on_categories(ctx, categories, search_groups)

        groups_research_member = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'research-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_deposit_member = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'deposit-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_intake_member = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'intake-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups_grp_member = [a for a in genquery.Query(ctx, "USER_GROUP_NAME", "USER_GROUP_NAME like 'grp-%%' " + search_sql + "AND USER_NAME = '{}' AND USER_ZONE = '{}'".format(user_name, user_zone))]
        groups = list(set(groups_research_member + groups_deposit_member + groups_intake_member + groups_grp_member + groups_dm))

    # groups.sort()
    group_list = []
    for groupname in groups:
        data_size = get_group_data_sizes(ctx, groupname)
        group_list.append([groupname, data_size])

    # Sort the list as requested by user
    sort_reverse = False
    if sort_order == 'desc':
        sort_reverse = True
    group_list.sort(key=lambda x: x[1][-1] if sort_on == 'size' else x[0], reverse=sort_reverse)

    # Only at this point we have the list in correct shape/order and can the limit and offset be applied
    # Format for datatables in frontend throughout yoda
    group_list_sorted = []
    group_slice = group_list[offset: offset + limit]

    for group_data in group_slice:
        members = group.members(ctx, group_data[0])
        group_list_sorted.append({"name": group_data[0], "size": group_data[1], "member_count": len(list(members))})

    return {'total': len(group_list), 'items': group_list_sorted}


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
    member_type = groups.user_role(ctx, user.full_name(ctx), group_name)
    if member_type not in ['reader', 'normal', 'manager']:
        category = groups.group_category(ctx, group_name)
        if not groups.user_is_datamanager(ctx, category, user.full_name(ctx)):
            if user.user_type(ctx) != 'rodsadmin':
                return api.Error('not_allowed', 'Insufficient permissions')

    labels = []
    research = []
    vault = []
    revision = []
    total = []
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
        total.append(temp[4])

    # example: {'labels': ['2022-06-01', '2022-06-02', '2022-06-03'], 'research': [123, 456, 789], 'vault': [666, 777, 888], 'revision': [200, 300, 400], 'total': [989, 1533, 2077]}
    return {'labels': labels, 'research': research, 'vault': vault, 'revision': revision, 'total': total}


@api.make()
def api_resource_category_stats(ctx):
    """Collect storage stats of last month for categories.
    Storage is summed up for each category.

    :param ctx: Combined type of a callback and rei struct

    :returns: Storage stats of last month for a list of categories
    """
    categories = get_categories(ctx)

    # Non-admin users don't have access to category storage statistics.
    # This makes sure the table is not presented in the frontend.
    if len(categories) == 0:
        return {'categories': [], 'external_filter': ''}

    # Continue for admins and datamanagers
    storage = {}

    # Go through current groups of current categories.
    # This function has no historic value so it is allowed to do so
    for category in categories:
        storage[category] = {'total': 0, 'research': 0, 'vault': 0, 'revision': 0, 'internal': 0, 'external': 0}

        # for all groups in category
        groups = get_groups_on_categories(ctx, [category])
        for groupname in groups:
            if groupname.startswith(('research', 'deposit', 'intake', 'grp')):
                # Only check the most recent storage measurement
                iter = list(genquery.Query(ctx,
                            ['META_USER_ATTR_VALUE', 'ORDER_DESC(META_USER_ATTR_NAME)', 'USER_NAME', 'USER_GROUP_NAME'],
                            "META_USER_ATTR_VALUE like '[\"{}\",%%' AND META_USER_ATTR_NAME like '{}%%' AND USER_NAME = '{}'".format(category, constants.UUMETADATAGROUPSTORAGETOTALS, groupname),
                            offset=0, limit=1, output=genquery.AS_LIST))

                for row in iter:
                    temp = jsonutil.parse(row[0])

                    storage[category]['total'] += temp[4]
                    storage[category]['research'] += temp[1]
                    storage[category]['vault'] += temp[2]
                    storage[category]['revision'] += temp[3]

    # Now go through all totals
    all_storage = []

    # Totalization for the entire instance.
    instance_totals = {'total': 0, 'research': 0, 'vault': 0, 'revision': 0}

    # Member counts
    cat_members = {}
    members_total = []
    for category in categories:
        members = []
        # this information is only available for yoda-admins
        for groupname in get_groups_on_categories(ctx, [category]):
            group_members = list(group.members(ctx, groupname))
            for gm in group_members:
                members.append(gm[0])
                members_total.append(gm[0])
        # deduplicate member list
        cat_members[category] = list(set(members))

    cat_members['YODA_INSTANCE_TOTAL'] = list(set(members_total))

    def count_externals(members):
        return len([member for member in members if not yoda_names.is_internal_user(member)])

    def count_internals(members):
        return len([member for member in members if yoda_names.is_internal_user(member)])

    for category in categories:
        storage_humanized = {}
        # humanize storage sizes for the frontend
        for type in ['total', 'research', 'vault', 'revision']:
            storage_humanized[type] = misc.human_readable_size(1.0 * storage[category][type])
            instance_totals[type] += 1.0 * storage[category][type]

        users = {'internals': count_internals(cat_members[category]), 'externals': count_externals(cat_members[category])}
        all_storage.append({'category': category,
                            'storage': storage_humanized,
                            'users': users})

    # Add the yoda instance information as an extra row with category name YODA_INSTANCE_TOTAL
    # So the frontend can distinguish instance totals from real category totals
    users = {'internals': count_internals(cat_members['YODA_INSTANCE_TOTAL']), 'externals': count_externals(cat_members['YODA_INSTANCE_TOTAL'])}
    all_storage.append({'category': "YODA_INSTANCE_TOTAL",
                        'storage': {'total': misc.human_readable_size(instance_totals['total']),
                                    'research': misc.human_readable_size(instance_totals['research']),
                                    'vault': misc.human_readable_size(instance_totals['vault']),
                                    'revision': misc.human_readable_size(instance_totals['revision'])},
                        'users': users})

    return {'categories': sorted(all_storage, key=lambda d: d['category']),
            'external_filter': ', '.join(config.external_users_domain_filter)}


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

    # Initialize to prevent errors in log when no data has been registered yet.
    min_year = -1
    min_month = -1

    # find minimal registered date registered.
    iter = list(genquery.Query(ctx, ['ORDER(META_USER_ATTR_NAME)'],
                               "META_USER_ATTR_NAME like '{}%%' and USER_TYPE = 'rodsgroup'".format(constants.UUMETADATAGROUPSTORAGETOTALS),
                               offset=0, limit=1, output=genquery.AS_LIST))

    for row in iter:
        min_year = int(row[0][-10:-6])
        min_month = int(row[0][-5:-3])

    if min_month == -1:
        # if min_month == -1 no minimal date was found. Consequently, stop further processing
        return {'storage': [], 'dates': []}

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
            if group.startswith(('research', 'deposit', 'intake', 'grp')):
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
                if group.startswith(('research', 'deposit', 'intake', 'grp')):
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
            if group.startswith(('research', 'deposit', 'intake', 'grp')):
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
        "USER_GROUP_NAME = '" + groupName + "' AND  META_USER_ATTR_NAME IN('category','subcategory')",
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

    return groups


@rule.make()
def rule_resource_store_storage_statistics(ctx):
    """
    For all categories present, store all found storage data for each group belonging to these categories.

    Store as metadata on group level as [category, research, vault, revision, total]

    :param ctx:  Combined type of a callback and rei struct

    :returns: Storage data for each group of each category
    """
    zone = user.zone(ctx)

    dt = datetime.today()
    md_storage_date = constants.UUMETADATAGROUPSTORAGETOTALS + dt.strftime("%Y_%m_%d")

    # Delete previous data for this particular day if present at all
    # Each group should only have one aggrageted totals attribute per day
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE, USER_GROUP_NAME",
        "META_USER_ATTR_NAME = '" + md_storage_date + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        if (md_storage_date, row[0], '') not in list(avu.of_group(ctx, row[1])):
            continue
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
            # Look at research, deposit, intake and grp groups
            if group.startswith(('research', 'deposit', 'intake', 'grp')):
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

                # For intake and grp groups.
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
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val)
                if group.startswith(('intake', 'grp')):
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val_other)

                log.write(ctx, 'Storage data collected and stored for current month <{}>'.format(group))
            else:  # except Exception:
                log.write(ctx, 'Skipping group as not prefixed with either research-, deposit-, intake- or grp- <{}>'.format(group))

    return 'ok'


@rule.make(inputs=[0, 1, 2], outputs=[])
def rule_resource_update_resc_arb_data(ctx, resc_name, bytes_free, bytes_total):
    """
    Update ARB data for a specific resource

    :param ctx:  Combined type of a callback and rei struct
    :param resc_name: Name of a particular unixfilesystem resource
    :param bytes_free: Free size on this resource, in bytes
    :param bytes_total: Total size of this resource, in bytes
    """
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "Error: insufficient permissions to run ARB data update rule.")
        return

    if not resource.exists(ctx, resc_name):
        log.write(ctx, "Error: could not find resource named '{}' for ARB update.".format(resc_name))
        return

    bytes_free_gb = int(bytes_free) / 2 ** 30
    bytes_free_percent = 100 * (float(bytes_free) / float(bytes_total))

    if resc_name in config.arb_exempt_resources:
        arb_status = constants.arb_status.EXEMPT
    elif bytes_free_gb >= config.arb_min_gb_free and bytes_free_percent > config.arb_min_percent_free:
        arb_status = constants.arb_status.AVAILABLE
    else:
        arb_status = constants.arb_status.FULL

    parent_resc_name = resource.get_parent_by_name(ctx, resc_name)

    manager = arb_data_manager.ARBDataManager()
    manager.put(ctx, resc_name, constants.arb_status.IGNORE)

    if parent_resc_name is not None and resource.get_type_by_name(ctx, parent_resc_name) == "passthru":
        manager.put(ctx, parent_resc_name, arb_status)


@rule.make()
def rule_resource_update_misc_arb_data(ctx):
    """Update ARB data for resources that are not covered by the regular process. That is,
       all resources that are neither unixfilesystem nor passthrough resources, as well as
       passthrough resources that do not have a unixfilesystem child resource.

       :param ctx: Combined type of a callback and rei struct
    """
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "Error: insufficient permissions to run ARB data update rule.")
        return

    manager = arb_data_manager.ARBDataManager()

    all_resources = resource.get_all_resource_names(ctx)
    ufs_resources = set(resource.get_resource_names_by_type(ctx, "unixfilesystem")
                        + resource.get_resource_names_by_type(ctx, "unix file system"))
    pt_resources  = set(resource.get_resource_names_by_type(ctx, "passthru"))

    for resc in all_resources:
        if resc in ufs_resources:
            pass
        elif resc not in pt_resources:
            manager.put(ctx, resc, constants.arb_status.IGNORE)
        else:
            child_resources = resource.get_children_by_name(ctx, resc)
            child_found = False
            for child_resource in child_resources:
                if child_resource in ufs_resources:
                    child_found = True
            # Ignore the passthrough resource if it does not have a UFS child resource
            if not child_found:
                manager.put(ctx, resc, constants.arb_status.IGNORE)


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
