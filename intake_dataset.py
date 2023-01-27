# -*- coding: utf-8 -*-
"""Functions for intake datasets."""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

from util import *


def intake_report_export_study_data(ctx, study_id):
    """ Get the information for the export functionality

    Retrieved metadata for a study:
    - dataset_date_created
    - wave
    - version
    - experiment_type
    - pseudocode
    - number of files
    - total file size

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Unique identifier op study
    :returns: returns datasets
    """
    zone = user.zone(ctx)

    result = genquery.row_iterator("COLL_NAME, COLL_PARENT_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                   "COLL_NAME like '/{}/home/grp-vault-{}%' AND META_COLL_ATTR_NAME IN ('dataset_id', 'dataset_date_created', 'wave', 'version', 'experiment_type', 'pseudocode')".format(zone, study_id),
                                   genquery.AS_LIST, ctx)

    datasets = {}
    for row in result:
        path = row[0]
        try:
            datasets[path][row[2]] = row[3]
        except KeyError:
            datasets[path] = {row[2]: row[3]}

    real_datasets = {}
    for set_path in datasets:
        if 'dataset_date_created' in datasets[set_path]:
            real_datasets[set_path] = datasets[set_path]
            # collect total file size and total amount of files
            real_datasets[set_path]['totalFileSize'] = 0
            real_datasets[set_path]['totalFiles'] = 0

            # get the filesize and file count
            result = genquery.row_iterator("count(DATA_ID), sum(DATA_SIZE)",
                                           "COLL_NAME like '{}%'".format(set_path),
                                           genquery.AS_LIST, ctx)
            for row in result:
                real_datasets[set_path]['totalFiles'] = int(row[0]) / 2
                totalFileSize = 0
                if row[1]:
                    totalFileSize = int(row[1])
                real_datasets[set_path]['totalFileSize'] = totalFileSize / 2

    return real_datasets


def intake_youth_get_datasets_in_study(ctx, study_id):
    """Get the of datasets (with relevant metadata) in a study.

    Retrieved metadata:
    - 'dataset_date_created'
    - 'wave'
    - 'version'
    - 'experiment_type'

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Unique identifier op study

    :returns: Dict with datasets and relevant metadata.
    """
    zone = user.zone(ctx)

    result = genquery.row_iterator("COLL_NAME, COLL_PARENT_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                   "COLL_NAME like '/{}/home/grp-vault-{}%' AND META_COLL_ATTR_NAME IN ('dataset_id', 'dataset_date_created', 'wave', 'version', 'experiment_type', 'pseudocode')".format(zone, study_id),
                                   genquery.AS_LIST, ctx)

    datasets = {}

    # Construct all datasets.
    for row in result:
        dataset = row[0]
        attribute_name = row[2]
        attribute_value = row[3]

        if attribute_name in ['dataset_date_created', 'wave', 'version', 'experiment_type', 'pseudocode']:
            if attribute_name in ['version', 'experiment_type']:
                val = attribute_value.lower()
                # datasets[dataset][attribute_name] = attribute_value.lower()
            else:
                val = attribute_value
                # datasets[dataset][attribute_name] = attribute_value
            try:
                datasets[dataset][attribute_name] = val
            except KeyError:
                datasets[dataset] = {attribute_name: val}

    return datasets


def intake_youth_dataset_counts_per_study(ctx, study_id):
    """"Get the counts of datasets wave/experimenttype.

    In the vault a dataset is always located in a folder.
    Therefore, looking at the folders only is enough.

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Unique identifier op study

    :returns: Dict with counts of datasets wave/experimenttype
    """
    datasets = intake_youth_get_datasets_in_study(ctx, study_id)

    dataset_type_counts = {}
    # Loop through datasets and count wave and experimenttype.
    for dataset in datasets:
        # Meta attribute 'dataset_date_created' defines that a folder holds a complete set.
        if 'dataset_date_created' in datasets[dataset]:
            type = datasets[dataset]['experiment_type']
            wave = datasets[dataset]['wave']
            version = datasets[dataset]['version']

            try:
                dataset_type_counts[type][wave][version] += 1
            except KeyError:
                if type not in dataset_type_counts:
                    dataset_type_counts[type] = {wave: {version: 1}}
                elif wave not in dataset_type_counts[type]:
                    dataset_type_counts[type][wave] = {version: 1}
                else:
                    dataset_type_counts[type][wave][version] = 1

    return dataset_type_counts


def vault_aggregated_info(ctx, study_id):
    """Collects aggregated information for raw and processed datasets.

    Collects the following information for RAW and PROCESSED datasets.
    Including a totalisation of this all (raw/processed is kept in VERSION)
        - Total datasets
        - Total files
        - Total file size
        - File size growth in a month
        - Datasets growth in a month
        - Pseudocodes  (distinct)

    :param ctx:      Combined type of a callback and rei struct
    :param study_id: Unique identifier op study

    :returns: Dict with aggregated information for raw and processed datasets
    """
    datasets = intake_youth_get_datasets_in_study(ctx, study_id)

    dataset_count = {'raw': 0, 'processed': 0}
    dataset_growth = {'raw': 0, 'processed': 0}
    dataset_file_count = {'raw': 0, 'processed': 0}
    dataset_file_size = {'raw': 0, 'processed': 0}
    dataset_file_growth = {'raw': 0, 'processed': 0}
    dataset_pseudocodes = {'raw': [], 'processed': []}

    # Determine full last month reference point
    import time
    from datetime import datetime, date, timedelta

    last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
    month = int(last_day_of_prev_month.strftime("%m"))
    year = int(last_day_of_prev_month.strftime("%Y"))

    last_month = int(time.time() - int(datetime(year, month, int(date.today().strftime("%d")), 0, 0, 0).strftime('%s')))

    dataset_paths = []
    for dataset in datasets:
        # Meta attribute 'dataset_date_created' defines that a folder holds a complete set.
        if 'dataset_date_created' in datasets[dataset]:
            dataset_paths.append(dataset)

            if datasets[dataset]['version'].lower() == 'raw':
                version = 'raw'
            else:
                version = 'processed'

            # if version in ['raw', 'processed']:
            dataset_count[version] += 1

            try:
                date_created = int(datasets[dataset]['dataset_date_created'])
            except Exception:
                # This is nonsense and arose from an erroneous situation
                date_created = last_month

            if date_created - last_month >= 0:
                dataset_growth[version] += 1

            try:
                pseudocode = datasets[dataset]['pseudocode']
                if pseudocode not in dataset_pseudocodes[version]:
                    dataset_pseudocodes[version].append(pseudocode)
            except KeyError:
                continue

    zone = user.zone(ctx)
    result = genquery.row_iterator("DATA_NAME, COLL_NAME, DATA_SIZE, COLL_CREATE_TIME",
                                   "COLL_NAME like '/{}/home/grp-vault-{}%'".format(zone, study_id),
                                   genquery.AS_LIST, ctx)

    for row in result:
        coll_name = row[1]
        data_size = int(row[2])
        coll_create_time = int(row[3])

        # Check whether the file is part of a dataset.
        part_of_dataset = False
        for dataset in dataset_paths:
            if dataset in coll_name:
                part_of_dataset = True
                break

        # File is part of dataset.
        if part_of_dataset:
            # version = datasets[dataset]['version']

            if datasets[dataset]['version'].lower() == 'raw':
                version = 'raw'
            else:
                version = 'processed'

            dataset_file_count[version] += 1
            dataset_file_size[version] += data_size

            if coll_create_time - last_month >= 0:
                dataset_file_growth[version] += data_size

    return {
        'total': {
            'totalDatasets': dataset_count['raw'] + dataset_count['processed'],
            'totalFiles': dataset_file_count['raw'] + dataset_file_count['processed'],
            'totalFileSize': dataset_file_size['raw'] + dataset_file_size['processed'],
            'totalFileSizeMonthGrowth': dataset_file_growth['raw'] + dataset_file_growth['processed'],
            'datasetsMonthGrowth': dataset_growth['raw'] + dataset_growth['processed'],
            'distinctPseudoCodes': len(dataset_pseudocodes['raw']) + len(dataset_pseudocodes['processed']),
        },
        'raw': {
            'totalDatasets': dataset_count['raw'],
            'totalFiles': dataset_file_count['raw'],
            'totalFileSize': dataset_file_size['raw'],
            'totalFileSizeMonthGrowth': dataset_file_growth['raw'],
            'datasetsMonthGrowth': dataset_growth['raw'],
            'distinctPseudoCodes': len(dataset_pseudocodes['raw']),
        },
        'notRaw': {
            'totalDatasets': dataset_count['processed'],
            'totalFiles': dataset_file_count['processed'],
            'totalFileSize': dataset_file_size['processed'],
            'totalFileSizeMonthGrowth': dataset_file_growth['processed'],
            'datasetsMonthGrowth': dataset_growth['processed'],
            'distinctPseudoCodes': len(dataset_pseudocodes['processed']),
        },
    }
