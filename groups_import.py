# -*- coding: utf-8 -*-
"""Functions related to importing group data."""

__copyright__ = 'Copyright (c) 2018-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from iteration_utilities import duplicates, unique_everseen

from util import *


def process_csv_line(ctx, line):
    """Process a line as found in the csv consisting of
       category, subcategory, groupname, managers, members and viewers,
       and optionally schema id and expiration date.

    :param ctx:      Combined type of a ctx and rei struct
    :param line:     Dictionary of labels and corresponding lists of values

    :returns: Tuple of processed row data (None if error), and error message
    """

    if (not ('category' in line and len(line['category']))
        or not ('subcategory' in line and len(line['subcategory']))
            or not ('groupname' in line and len(line['groupname']))):
        return None, "Row has a missing group name, category or subcategory"

    category = line['category'][0].strip().lower().replace('.', '')
    subcategory = line['subcategory'][0].strip()
    groupname = "research-" + line['groupname'][0].strip().lower()
    schema_id = line['schema_id'][0] if 'schema_id' in line and len(line['schema_id']) else ''
    expiration_date = line['expiration_date'][0] if 'expiration_date' in line and len(line['expiration_date']) else ''
    managers = []
    members = []
    viewers = []

    for column_name, item_list in sorted(line.items(), key=lambda line: line[0]):
        if column_name == '':
            return None, 'Column cannot have an empty label'
        elif column_name in get_csv_predefined_labels():
            continue
        elif not column_name_is_role_label(column_name):
            return None, "Column label '{}' is not a valid label.".format(column_name)

        for i in range(len(item_list)):
            item_list[i] = item_list[i].strip().lower()
            username = item_list[i]
            if not yoda_names.is_email_username(username):
                return None, 'Username "{}" is not a valid email address.'.format(
                    username)

        if column_name.lower() == 'manager' or column_name.lower().startswith("manager:"):
            managers.extend(item_list)
        elif column_name.lower() == 'member' or column_name.lower().startswith("member:"):
            members.extend(item_list)
        elif column_name.lower() == 'viewer' or column_name.lower().startswith("viewer:"):
            viewers.extend(item_list)

    if len(managers) == 0:
        return None, "Group must have a group manager"

    if not yoda_names.is_valid_category(category):
        return None, '"{}" is not a valid category name.'.format(category)

    if not yoda_names.is_valid_subcategory(subcategory):
        return None, '"{}" is not a valid subcategory name.'.format(subcategory)

    if not yoda_names.is_valid_groupname("research-" + groupname):
        return None, '"{}" is not a valid group name.'.format(groupname)

    if not yoda_names.is_valid_schema_id(schema_id):
        return None, '"{}" is not a valid schema id.'.format(schema_id)

    if not yoda_names.is_valid_expiration_date(expiration_date):
        return None, '"{}" is not a valid expiration date.'.format(expiration_date)

    row_data = (category, subcategory, groupname, managers,
                members, viewers, schema_id, expiration_date)
    return row_data, None


def column_name_is_role_label(column_name):
    return (column_name.lower() in get_role_labels()
            or column_name.lower().startswith(tuple(map(lambda s: s + ":", get_role_labels()))))


def get_role_labels():
    return ['viewer', 'member', 'manager']


def get_csv_possible_labels():
    return ['category', 'subcategory', 'groupname', 'viewer', 'member', 'manager', 'schema_id', 'expiration_date']


def get_csv_required_labels():
    return ['category', 'subcategory', 'groupname']


def get_csv_predefined_labels():
    """These labels should not repeat"""
    return ['category', 'subcategory', 'groupname', 'schema_id', 'expiration_date']


def get_duplicate_columns(fields_list):
    fields_seen = set()
    duplicate_fields = set()

    for field in fields_list:
        if field in get_csv_predefined_labels():
            if field in fields_seen:
                duplicate_fields.add(field)
            else:
                fields_seen.add(field)

    return duplicate_fields


def parse_csv_file(ctx):
    extracted_data = []
    row_number = 0

    # Validate header columns (should be first row in file)

    # Are all required fields present?
    for label in get_csv_required_labels():
        if label not in reader.fieldnames:
            _exit_with_error(
                'CSV header is missing compulsory field "{}"'.format(label))

    # Check that all header names are valid
    possible_labels = get_csv_possible_labels()
    for label in header:
        if label not in possible_labels:
            _exit_with_error(
                'CSV header contains unknown field "{}"'.format(label))

    # duplicate fieldnames present?
    duplicate_columns = get_duplicate_columns(reader.fieldnames)
    if (len(duplicate_columns) > 0):
        _exit_with_error("File has duplicate column(s): " + str(duplicate_columns))

    # Start processing the actual group data rows
    for line in lines:
        row_number += 1
        rowdata, error = process_csv_line(line)

        if error is None:
            extracted_data.append(rowdata)
        else:
            _exit_with_error("Data error in in row {}: {}".format(
                str(row_number), error))

    return extracted_data


def get_duplicate_groups(row_data):
    group_names = list(map(lambda r: r[2], row_data))
    return list(unique_everseen(duplicates(group_names)))


def parse_data(ctx, csv_header_and_data):
    """Process contents of csv data consisting of header and rows of data.

    :param ctx:                 Combined type of a ctx and rei struct
    :param csv_header_and_data: CSV data holding a head conform description and the actual row data

    :returns: Dict containing error and the extracted data
    """
    extracted_data = []

    csv_lines = csv_header_and_data.splitlines()
    header = csv_lines[0]
    import_lines = csv_lines[1:]

    # List of dicts each containing label / list of values pairs.
    lines = []
    header_cols = header.split(',')
    for import_line in import_lines:
        data = import_line.split(',')
        if len(data) != len(header_cols):
            return [], 'Amount of header columns differs from data columns.'
        # A kind of MultiDict
        # each key is a header column
        # each item is a list of items for that header column
        line_dict = {}
        for x in range(0, len(header_cols)):
            if header_cols[x] == '':
                if x == len(header_cols) - 1:
                    return [], "Header row ends with ','"
                else:
                    return [], 'Empty column description found in header row.'

            # EVERY row should have all the headers that were listed at the top of the file
            if header_cols[x] not in line_dict:
                line_dict[header_cols[x]] = []

            if len(data[x]):
                line_dict[header_cols[x]].append(data[x])

        lines.append(line_dict)

    for line in lines:
        rowdata, error = process_csv_line(ctx, line)

        if error is None:
            extracted_data.append(rowdata)
        else:
            # End processing of csv data due to erroneous input
            return extracted_data, "Data error: {}".format(error)

    duplicate_groups = get_duplicate_groups(extracted_data)
    if len(duplicate_groups) > 0:
        return [], "CSV data has one or more duplicate groups: " + ",".join(duplicate_groups)

    return extracted_data, ''
