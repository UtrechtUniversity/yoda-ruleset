"""Functions for statistics module."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2018-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import copy
import time
from datetime import date, datetime
from typing import Dict, List, Optional

import genquery
from dateutil.relativedelta import relativedelta

import groups
from util import *

__all__ = ['api_resource_browse_group_data',
           'api_resource_monthly_category_stats',
           'api_resource_category_stats',
           'api_resource_full_year_differentiated_group_storage',
           'rule_resource_store_pregenerated_exportdata',
           'rule_resource_store_storage_statistics',
           'rule_resource_research',
           'rule_resource_vault']


@api.make()
def api_resource_browse_group_data(ctx: rule.Context,
                                   sort_on: str = 'name',
                                   sort_order: str = 'asc',
                                   offset: int = 0,
                                   limit: int = 10,
                                   search_groups: str = "") -> api.Result:
    """Get paginated group data groupname / size

    :param ctx:        Combined type of a callback and rei struct
    :param sort_on:    Column to sort on ('name', 'modified' or size)
    :param sort_order: Column sort order ('asc' or 'desc')
    :param offset:     Offset to start browsing from
    :param limit:      Limit number of results
    :param search_groups: Search specific groups

    :returns: Dict with paginated collection contents
    """
    # Find latest registered date
    date_ref = get_date_reference(ctx, 'desc')
    if date_ref is not None:
        latest_date = f"{date_ref.year}_{date_ref.month:02}"
    else:
        return {'total': 0, 'items': []}

    # Get user's search
    search_filter = ""
    if search_groups:
        search_filter = f"AND USER_GROUP_NAME LIKE '%%{search_groups[:63]}%%' "  # Max characters allowed in group name is 63.

    # Query all storage data
    storage_data = get_storage_data(ctx, search_filter, latest_date)

    # Initialize group data
    item_list = []
    groups_list = get_user_groups_for_stats(ctx, search_filter)

    # Process data sizes for sorting
    for row in storage_data:
        # Filter out groups that user is not part of
        if row[2] in groups_list:
            # the replace is merely here due to earlier (erroneous0 values that were added as '' in json where this should have been ""
            temp = jsonutil.parse(row[0].replace("'", '"'))

            # [group_name [research_storage, vault_storage, revision_storage, total_storage]]
            data_size = [int(temp[1]), int(temp[2]), int(temp[3]), int(temp[4])]
            item_list.append([row[2], data_size])
            groups_list.remove(row[2])

    # Set groups that were not processed (for lack of data) to empty
    for grp in groups_list:
        item_list.append([grp, [0, 0, 0, 0]])

    # Sort the list as requested by user
    sort_reverse = sort_order == 'desc'
    item_list.sort(key=lambda x: x[1][-1] if sort_on == 'size' else x[0], reverse=sort_reverse)

    # Only at this point we have the list in correct shape/order and can the limit and offset be applied
    # Format for datatables in frontend throughout yoda
    item_list_sorted = []
    group_slice = item_list[offset: offset + limit]

    for group_data in group_slice:
        members = group.members(ctx, group_data[0])
        item_list_sorted.append({"name": group_data[0], "size": group_data[1], "member_count": len(list(members))})

    return {'total': len(item_list), 'items': item_list_sorted}


@api.make()
def api_resource_full_year_differentiated_group_storage(ctx: rule.Context, group_name: str) -> api.Result:
    """Return the full range of registered storage data differentiated into vault/research/revision/total.

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
def api_resource_category_stats(ctx: rule.Context) -> api.Result:
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

    # Find latest registered date
    date_ref = get_date_reference(ctx, 'desc')

    attr_name = constants.UUMETADATAGROUPSTORAGETOTALS
    if date_ref is not None:
        attr_name += f"{date_ref.year}_{date_ref.month:02}"

    # Retrieve storage statistics of groups.
    iter = genquery.Query(ctx,
                          ['USER_GROUP_NAME', 'ORDER_DESC(META_USER_ATTR_NAME)', 'META_USER_ATTR_VALUE'],
                          "META_USER_ATTR_NAME like '{}%%'".format(attr_name),
                          output=genquery.AS_LIST)

    # Go through storage statistics of groups.
    storage = {}
    group_counted = []
    for group_name, _storage_attribute, storage_json in iter:
        # Check if group is valid and has not been counted yet.
        if group_name.startswith(('research-', 'deposit-', 'intake-', 'grp-')) and group_name not in group_counted:
            # Add group to list of groups counted for category statistics.
            group_counted.append(group_name)

            # Add group to category statistics.
            category, research, vault, revisions, total = jsonutil.parse(storage_json)
            storage.setdefault(category, {'research': 0, 'vault': 0, 'revision': 0, 'total': 0})
            storage[category]['research'] += research
            storage[category]['vault'] += vault
            storage[category]['revision'] += revisions
            storage[category]['total'] += total

    # Retrieve groups and their members.
    iter = genquery.Query(ctx,
                          ['USER_GROUP_NAME', 'USER_NAME'],
                          "USER_TYPE != 'rodsgroup'",
                          output=genquery.AS_LIST)

    # Calculate number of members per type per group.
    members = {}
    for group_name, user_name in iter:
        members.setdefault(group_name, {'internal': set(), 'external': set()})
        if yoda_names.is_internal_user(user_name):
            members[group_name]['internal'].add(user_name)
        else:
            members[group_name]['external'].add(user_name)

    # Calculate category members and storage totals.
    instance_totals = {'total': 0, 'research': 0, 'vault': 0, 'revision': 0, 'internals': set(), 'externals': set()}
    all_storage = []
    for category in categories:
        if category not in storage:
            continue

        # Calculate category members and totals.
        internals = set()
        externals = set()
        for group_name in get_groups_on_categories(ctx, [category]):
            members.setdefault(group_name, {'internal': set(), 'external': set()})
            internals.update(members[group_name]['internal'])
            externals.update(members[group_name]['external'])

        # Deduplicate group members.
        users = {'internals': len(internals), 'externals': len(externals)}

        # Count instance totals.
        instance_totals['internals'].update(internals)
        instance_totals['externals'].update(externals)

        # Humanize storage sizes for the frontend and calculate instance totals.
        storage_humanized = {}
        for storage_type in ['research', 'vault', 'revision', 'total']:
            storage_humanized[storage_type] = misc.human_readable_size(1.0 * storage[category][storage_type])
            instance_totals[storage_type] += 1.0 * storage[category][storage_type]

        all_storage.append({'category': category,
                            'storage': storage_humanized,
                            'users': users})

    # Add the Yoda instance information as an extra row with category name YODA_INSTANCE_TOTAL.
    # So the frontend can distinguish instance totals from real category totals.
    all_storage.append({'category': "YODA_INSTANCE_TOTAL",
                        'storage': {'total': misc.human_readable_size(instance_totals['total']),
                                    'research': misc.human_readable_size(instance_totals['research']),
                                    'vault': misc.human_readable_size(instance_totals['vault']),
                                    'revision': misc.human_readable_size(instance_totals['revision'])},
                        'users': {'internals': len(instance_totals['internals']),
                                  'externals': len(instance_totals['externals'])}})

    return {'categories': sorted(all_storage, key=lambda d: d['category']),
            'external_filter': ', '.join(config.external_users_domain_filter)}


@api.make()
def api_resource_monthly_category_stats(ctx: rule.Context) -> api.Result:
    """Collect storage stats for all twelve months based upon categories a user is datamanager of.

    Statistics gathered:
    - Category
    - Subcategory
    - Groupname
    - n columns - one per month, with used storage count in bytes

    :param ctx:  Combined type of a callback and rei struct

    :returns: API status
    """

    pregenerated_data_time_threshold = int(time.time()) - 72 * 3600
    try:
        pregenerated_data = pregenerated_data_manager.pregenerated_data_load("statistics-export")
    except Exception as e:
        log.write(ctx, "Error while loading pregenerated data for statistics export: " + str(e)
                  + ". Generating data instead.")
        pregenerated_data = None

    if (pregenerated_data is None
            or pregenerated_data['metadata']['timestamp'] < pregenerated_data_time_threshold):
        data = get_resource_monthly_category_stats(ctx)
        data.pop('metadata')
        return data
        # Don't save this data as pregenerated data. The pregenerated data
        # needs to be created by the rods user in order to ensure that it includes
        # all data, rather than only the data that the current user has access to.
    else:
        return filter_pregenerated_exportdata(ctx, pregenerated_data)


def filter_pregenerated_exportdata(ctx: rule.Context, inputdata: Dict) -> Dict:
    """Filter pregenerated statistics export data for use by the frontend
       code. The main goal of this function is to filter out data that the
       present user should not have access to. We also remove metadata, because
       it's not needed in the frontend.

       :param ctx:       Combined type of a callback and rei struct
       :param inputdata: Pregenerated data

       :returns: Filtered data
    """
    output_storagedata = []
    user_accessible_groups = set(get_user_groups_for_stats(ctx))

    for groupdata in inputdata['storage']:
        if groupdata.get('groupname', '') in user_accessible_groups:
            output_storagedata.append(groupdata)

    return {'storage': output_storagedata,
            'dates': copy.deepcopy(inputdata['dates'])
            }


@rule.make()
def rule_resource_store_pregenerated_exportdata(ctx: rule.Context) -> None:
    """Collects and store pregenerated data for the statistics export function.

       :param ctx: Combined type of a callback and rei struct

       :raises Exception: if unable to store the pregenerated data
    """
    data = get_resource_monthly_category_stats(ctx)
    try:
        pregenerated_data_manager.pregenerated_data_save("statistics-export", data)
    except Exception as e:
        log.write(ctx, "Unable to store pregenerated data for statistics export: " + str(e))
        raise e


def get_resource_monthly_category_stats(ctx: rule.Context) -> Dict:
    """Collect monthly category statistics for the export function in the portal.

       :param ctx:  Combined type of a callback and rei struct

       :returns:       Dictionary with monthly category statistics

    """
    user_zone = user.zone(ctx)

    current_date = date(datetime.now().year, datetime.now().month, datetime.now().day)
    min_date = get_date_reference(ctx, "asc")

    if min_date is None:
        return {'storage': [], 'dates': []}

    # Create dict with all groups that will contain list of storage values corresponding to complete range from minimal date till now.
    group_storage = {}

    # All storage periods (yyyy-mm) for frontend
    storage_dates = []

    # A group always has 1 distinct category and 1 distinct subcateory
    group_catdata = {}

    # Get category info and initialize group data
    zone_filter = "USER_ZONE = '{}' ".format(user_zone)
    group_filter = "AND USER_GROUP_NAME like 'research-%%' || like 'deposit-%%' || like 'intake-%%' || like 'grp-%%' "
    meta_filter = "AND META_USER_ATTR_NAME IN ('category', 'subcategory') "
    category_list = list(genquery.Query(ctx,
                                        ["ORDER(USER_GROUP_NAME)", "META_USER_ATTR_NAME", "META_USER_ATTR_VALUE"],
                                        zone_filter + group_filter + meta_filter))

    groups_list = get_user_groups_for_stats(ctx)

    category = ''
    subcategory = ''
    for row in category_list:
        group = row[0]
        attr_name = row[1]
        attr_value = row[2]

        if attr_name == 'category':
            category = attr_value

        if attr_name == 'subcategory':
            subcategory = attr_value

        if group in groups_list:
            group_storage[group] = []
            group_catdata[group] = {
                'category': category,
                'subcategory': subcategory
            }

    # Get full storage data info
    storage_data = get_storage_data(ctx)

    # Loop from earliest data to now and find storage for each group/date combination
    record_count = 0
    while min_date <= current_date:
        date_reference = f"{min_date.year}_{min_date.month:02}"
        storage_dates.append(date_reference)
        attr_name = constants.UUMETADATAGROUPSTORAGETOTALS + date_reference
        skip_group = []

        for row in storage_data:
            storage_date = row[1]
            group = row[2]

            # If date reference matches storage date and group is one of user's groups, append total storage value.
            if group not in skip_group and group in groups_list and date_reference in storage_date:
                # There might be old data that have ' instead of " in the json.
                data_size = jsonutil.parse(row[0].replace("'", '"'))

                # data_size: [category, research_storage, vault_storage, revision_storage, total_storage]
                total_storage = data_size[4]

                group_storage[group].append(total_storage)
                skip_group.append(group)

        # Iterate all groups to initialize current month's data if there was no match in storage data
        for group in groups_list:
            if len(group_storage[group]) == record_count:
                group_storage[group].append(0)

        # Increment time period by 1 month
        min_date = min_date + relativedelta(months=+1)
        record_count += 1

    all_storage = [
        {
            'category': group_catdata[group]['category'],
            'subcategory': group_catdata[group]['subcategory'],
            'groupname': group,
            'storage': group_storage[group]
        }
        for group in group_storage
    ]

    timestamp = int(time.time())
    readable_timestamp = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')
    metadata = {'timestamp': timestamp, 'readable_timestamp': readable_timestamp}

    return {'storage': all_storage, 'dates': storage_dates, 'metadata': metadata}


@rule.make()
def rule_resource_store_storage_statistics(ctx: rule.Context) -> str:
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

                # write as metadata (kv-pair) to current group
                if group.startswith(('research', 'deposit')):
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val)
                if group.startswith(('intake', 'grp')):
                    avu.associate_to_group(ctx, group, md_storage_date, storage_val_other)

                log.write(ctx, 'Storage data collected and stored for current month <{}>'.format(group))
            else:  # except Exception:
                log.write(ctx, 'Skipping group as not prefixed with either research-, deposit-, intake- or grp- <{}>'.format(group))

    return 'ok'


def get_groups_on_categories(ctx: rule.Context, categories: List, search_groups: str = "") -> List:
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

    group_filter = "USER_GROUP_NAME like 'research-%%' || like 'deposit-%%'  || like 'intake-%%' || like 'grp-%%' "

    for category in categories:
        iter = genquery.row_iterator(
            "USER_NAME",
            group_filter + search_sql + "AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE = '" + category + "' ",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            groupName = row[0]
            groups.append(groupName)

    return groups


def get_categories(ctx: rule.Context) -> List:
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


def get_groups_on_category(ctx: rule.Context, category: str) -> List:
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


def get_date_reference(ctx: rule.Context, order: str) -> Optional[date]:
    """Get first date reference in storage data

    :param ctx:           Combined type of a callback and rei struct
    :param order:         Specified order (ascending or descending)

    :returns: Date reference in storage data
    """
    column_name = ""

    if order == "desc":
        column_name = "ORDER_DESC(META_USER_ATTR_NAME)"
    elif order == "asc":
        column_name = "ORDER(META_USER_ATTR_NAME)"

    # Find registered date
    iter = list(genquery.Query(ctx,
                               column_name,
                               f"META_USER_ATTR_NAME LIKE '{constants.UUMETADATAGROUPSTORAGETOTALS}%%' and USER_TYPE = 'rodsgroup'",
                               offset=0, limit=1))

    if len(iter) > 0:  # If item found, save date
        return date(int(iter[0][-10:-6]), int(iter[0][-5:-3]), int(iter[0][-2:]))
    else:  # No minimum date found = no records
        return None


def get_storage_data(ctx: rule.Context, search_filter: str = "", date_ref: str = "") -> List:
    """Get all storage data

    :param ctx:           Combined type of a callback and rei struct
    :param search_filter: For specific search of groups
    :param date_ref:      For specific date reference

    :returns: All storage data on record
    """
    storage_data = []
    user_zone = user.zone(ctx)

    attr_name = constants.UUMETADATAGROUPSTORAGETOTALS
    if date_ref != "":
        attr_name += date_ref

    group_filter = "USER_GROUP_NAME LIKE 'research-%%' || LIKE 'deposit-%%'  || LIKE 'intake-%%' || LIKE 'grp-%%' "
    metadata_filter = f"AND META_USER_ATTR_NAME LIKE '{attr_name}%%' "
    zone_filter = f"AND USER_ZONE = '{user_zone}' "

    storage_data = list(genquery.Query(ctx,
                                       ['META_USER_ATTR_VALUE', 'ORDER_DESC(META_USER_ATTR_NAME)', 'USER_GROUP_NAME'],
                                       group_filter + search_filter + metadata_filter + zone_filter))

    return storage_data


def get_user_groups_for_stats(ctx: rule.Context, search_filter: str = "", user_name: Optional[str] = None, zone_name: Optional[str] = None) -> List[str]:
    """Get list of groups that a user has access to as a regular member, group manager or data manager.
       The results are limited to types of groups relevant for statistics
       (research, deposit, intake and legacy grp).

    :param ctx:           Combined type of a callback and rei struct
    :param search_filter: For specific search of groups
    :param user_name:     Name of user (None: current user)
    :param zone_name:     Name of user zone (None: zone of current user)

    :returns: All groups of current session's user
    """
    groups_list = []

    user_name = user.name(ctx) if user_name is None else user_name
    user_zone = user.zone(ctx) if zone_name is None else zone_name

    # Query all storage records
    group_filter = "USER_GROUP_NAME LIKE 'research-%%' || LIKE 'deposit-%%'  || LIKE 'intake-%%' || LIKE 'grp-%%' "
    zone_filter = f"AND USER_ZONE = '{user_zone}' "

    if user.is_admin(ctx, f"{user_name}#{user_zone}"):
        # All groups in zone
        groups_list = list(genquery.Query(ctx,
                                          "ORDER(USER_GROUP_NAME)",
                                          group_filter + zone_filter + search_filter))
    else:
        # Groups the user is member of
        user_filter = f"AND USER_NAME = '{user_name}' "
        group_member = list(genquery.Query(ctx,
                                           "ORDER(USER_GROUP_NAME)",
                                           group_filter + user_filter + search_filter))

        for grp in group_member:
            if grp not in groups_list:
                groups_list.append(grp)

        # Groups the user is datamanager of
        dmgroup_member = list(genquery.Query(ctx,
                                             "ORDER(USER_GROUP_NAME)",
                                             "USER_GROUP_NAME LIKE 'datamanager-%' " + user_filter))

        categories = []
        for grp in dmgroup_member:
            cat = grp.replace("datamanager-", "", 1)
            categories.append(cat)

        if len(categories) > 0:
            quoted_categories = [f"'{e}'" for e in categories]
            categories_string = f"({','.join(quoted_categories)})"
            group_dm = list(genquery.Query(ctx,
                                           "ORDER(USER_GROUP_NAME)",
                                           group_filter + search_filter + f"AND META_USER_ATTR_NAME = 'category' AND META_USER_ATTR_VALUE IN {categories_string}"))

            for grp in group_dm:
                if grp not in groups_list:
                    groups_list.append(grp)

    return groups_list


def rule_resource_research(rule_args, callback, rei):
    rule_args[0] = config.resource_research


def rule_resource_vault(rule_args, callback, rei):
    rule_args[0] = config.resource_vault
