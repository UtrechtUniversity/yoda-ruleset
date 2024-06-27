#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# This script modifies the data objects listed in CSV file.
# 
import subprocess
import genquery
import session_vars
import csv
import os.path


def errorcode(e):
      start = e.message.find(':')
      stop  = e.message.find(']')
      return  e.message[start + 1: stop]


def data_file_exists(resc_name, data_path, callback):
    # Verify that data file exists in given data path
    try:
        output = callback.msi_stat_vault(resc_name, data_path, "", "")
        type, size = output['arguments'][2], output['arguments'][3]
        if type == 'FILE':
            exists = True
        else:
            exists = False
    except RuntimeError as e:
        callback.writeLine("stdout","[msi_stat_vault failed on path '{}' with error - '{}'".format(data_path, errorcode(e)))
        return str(False), -1, "[msi_stat_vault failed on path '{}' with error - '{}'".format(data_path, errorcode(e))

    return exists, type, size

def count_replicas_on_path(data_id, repl_num, data_path, callback):
    # Count other replicas with same data path
    replicas_list = []
    resc_loc = ""

    rescloc_iter = genquery.row_iterator(
    "RESC_LOC, DATA_ID", 
    "DATA_ID = '{}' AND DATA_REPL_NUM = '{}'".format(data_id, repl_num),
    genquery.AS_LIST,
    callback)

    for row in rescloc_iter:
        resc_loc = row[0]


    replica_iter = genquery.row_iterator(
    "DATA_ID, DATA_REPL_NUM, RESC_LOC", 
    "DATA_PATH = '{}' AND RESC_LOC = '{}'".format(data_path, resc_loc),
    genquery.AS_LIST,
    callback)

    for row in replica_iter:
        if row[0] != data_id or row[1] != repl_num:
            replicas_list.append(row[0])

    return replicas_list


def calculate_chksum(resc_name, data_path, callback):
    #  Calculate checksum data file and compare it to the replica checksum.
    try:
        chksum_output = callback.msi_file_checksum(data_path, resc_name, '')
        chksum = chksum_output['arguments'][2]
    except RuntimeError as e:
        callback.writeLine("stdout","msi_file_checksum failed on path '{}' with error - '{}'".format(data_path, errorcode(e)))
        return -1, "msi_file_checksum failed on path '{}' with error - '{}'".format(data_path, errorcode(e))

    return chksum


def replica_compatibility(data_id, repl_num, resc_name, data_path, data_file_size, callback):
    # The data file should pass compatibility check with the replica
    replica_chksum = ""
    replica_size = ""

    replica_iter = genquery.row_iterator(
    "DATA_SIZE, DATA_CHECKSUM, RESC_LOC",
    "DATA_ID ='{}' AND DATA_REPL_NUM = '{}'".format(data_id, repl_num),
    genquery.AS_TUPLE,
    callback)

    for row in replica_iter:
        replica_size = row[0]
        replica_chksum = row[1]

    if replica_size == data_file_size:
        if replica_chksum:
            data_file_chksum = calculate_chksum(resc_name, data_path, callback)
            if data_file_chksum == replica_chksum:
                return True
        else:
            return True
    else:
        return False

def get_logical_path(data_id, callback):
    path = ""

    logicalpath_iter = genquery.row_iterator(
    "COLL_NAME, DATA_NAME",
    "DATA_ID ='{}'".format(data_id),
    genquery.AS_TUPLE,
    callback)

    for row in logicalpath_iter:
        path = row[0] + '/' + row[1]

    return path

def get_actual_data_path(data_id, repl_num, callback):
    path = ""

    path_iter = genquery.row_iterator(
    "DATA_PATH, RESC_LOC",
    "DATA_ID ='{}' AND DATA_REPL_NUM = '{}'".format(data_id, repl_num),
    genquery.AS_TUPLE,
    callback)

    for row in path_iter:
        path = row[0]

    return path
        

# Identify use case
def preconditions_for_data_object(data, run_type, dry_run, callback):

    expected_is_compatible = False 
    actual_is_compatible = False
    expected_linked_use = False
    actual_linked_use = False
    expected_replicas_list = []
    actual_replicas_list = []
    
    actual_data_path = get_actual_data_path(data['data_id'], data['data_repl_num'], callback)
    logical_path = get_logical_path(data['data_id'], callback)

    # Check if row has already been processed
    if actual_data_path == data['expected_data_path']:
        status = 'Row with data id: ' + data['data_id'] + ' is already processed.'
        callback.writeLine("stdout", 'Row with data id: ' + data['data_id'] + ' is ignored.')
        return True, 0, status

    # Data file exists or not
    expected_data_file_exists, expected_data_file_type, expected_data_file_size = data_file_exists(data['resc_name'], data['expected_data_path'], callback)

    actual_data_file_exists, actual_data_file_type, actual_data_file_size = data_file_exists(data['resc_name'], actual_data_path, callback)
    
    # Check compatibility
    if expected_data_file_exists:
        expected_is_compatible = replica_compatibility(data['data_id'], data['data_repl_num'], data['resc_name'], data['expected_data_path'], expected_data_file_size, callback)
    
    expected_replicas_list = count_replicas_on_path(data['data_id'], data['data_repl_num'], data['expected_data_path'], callback)
    if len(expected_replicas_list) == 0:
        expected_linked_use = False
    else:
        expected_linked_use = True

    if actual_data_file_exists:
        actual_is_compatible = replica_compatibility(data['data_id'], data['data_repl_num'], data['resc_name'], actual_data_path, actual_data_file_size, callback)
    
    actual_replicas_list = count_replicas_on_path(data['data_id'], data['data_repl_num'], actual_data_path, callback)
    if len(actual_replicas_list) == 0:
        actual_linked_use = False
    else:
        actual_linked_use = True

    if run_type == 'repair':
        if expected_data_file_exists and not expected_linked_use and expected_is_compatible and not actual_data_file_exists:
            callback.writeLine("stdout", "Data ID: " + data['data_id'] + " - Testcase: UC1")

            if dry_run == 'False':
                callback.writeLine("serverLog", "Modifying data object on path: " + logical_path + " for use case 1.")

            status = modify_data_object(data['data_id'], data['data_repl_num'], data['expected_data_path'], dry_run, callback)
            if status == '':
                return True, 0, status
            else:
                return False, -1, status    
        elif expected_data_file_exists and not expected_linked_use and expected_is_compatible and actual_data_file_exists and actual_linked_use and not actual_is_compatible:
            callback.writeLine("stdout", "Data ID: " + data['data_id'] + " - Testcase: UC2")

            if dry_run == 'False':
                callback.writeLine("serverLog", "Modifying data object on path: " + logical_path + " for use case 2.")

            status = modify_data_object(data['data_id'], data['data_repl_num'], data['expected_data_path'], dry_run, callback)
            if status == '':
                return True, 0, status
            else:
                return False, -1, status
        else:
            return False, -1, "Data ID: " + data['data_id'] + " does not match usecase 1 or usecase 2."
    
    elif run_type == 'clean':
        if not expected_is_compatible and not actual_is_compatible and actual_linked_use:
            callback.writeLine("stdout", "Data ID: " + data['data_id'] + " - Testcase: UC3")

            if dry_run == 'False':
                callback.writeLine("serverLog", "Unregistering replica on logical path: " + logical_path + " for use case 3.")

            if len(actual_replicas_list) == 1:
                # Use scope = data_object for unregistering the replica
                status = unregister_replica(data['data_repl_num'], logical_path, dry_run, callback, scope = 'object')
            elif len(actual_replicas_list) > 1: 
                # Unregister the replica
                status = unregister_replica(data['data_repl_num'], logical_path, dry_run, callback)

            if status == '':
                return True, 0, status
            else:
                return False, -1, status
        else:
            return False, -1, "Data ID: " + data['data_id'] + " does not match usecase 3."
    else:
        return False, -1, "Invalid run type parameter."

def modify_data_object(data_id, repl_num, data_path, dry_run, callback):
    # Modify the replica with correct data path
    if dry_run == 'False':
        try:
            status = subprocess.check_output(['iadmin', 'modrepl', 'data_id', data_id, 'replica_number', repl_num, 'DATA_PATH', data_path], stderr=subprocess.STDOUT)
        except Exception as e:
            status = e.output[e.output.find("ERROR:"):].rstrip()

        if "\n" in status:
            status = status.replace("\n", " ").strip()
        else:
            status = status.strip()
    else:
        status = ''

    return status

def unregister_replica(repl_num, logical_path, dry_run, callback, scope = 'replica'):
    if dry_run == 'False':
        if scope == 'object':
            try:
                status = subprocess.check_output(['iunreg', logical_path], stderr=subprocess.STDOUT)
            except Exception as e:
                status =  e.output[e.output.find("ERROR:"):].rstrip()
        else:
            try:
                status = subprocess.check_output(['iunreg', '-n', repl_num, '-N', '0', logical_path], stderr=subprocess.STDOUT)
            except Exception as e:
                status =  e.output[e.output.find("ERROR:"):].rstrip()
        status = status.strip()
    else:
        status = ''
    return status

def csv_unquote(s):
    return s.replace('""','"').strip('"')


def main(rule_args, callback, rei):

    input_file = global_vars["*input_file"]
    output_file = global_vars["*output_file"]
    dry_run = global_vars["*dry_run"]
    run_type = global_vars["*run_type"]
    # Read CSV
    with open(input_file, 'r') as csvfile, open(output_file, 'w') as result:
        reader = csv.DictReader(csvfile, delimiter = ";")
        fieldnames = reader.fieldnames + ['message']
        writer = csv.DictWriter(result, fieldnames, delimiter = ";", quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for row in reader:
            row['expected_data_path'] = csv_unquote(row['expected_data_path'])
            row['actual_data_path'] = csv_unquote(row['actual_data_path'])
            if row['processed'] in ('ERROR', 'NO'):
                boolvar, retCode, msg = preconditions_for_data_object(row, run_type, dry_run, callback)
                if retCode == 0:
                    if msg == '':
                        msg = 'Success'
                    row['processed'] = 'YES'
                    writer.writerow(dict(row, message=msg))
                else:
                    callback.writeLine("stdout", "Status: " + msg)
                    row['processed'] = 'ERROR'
                    writer.writerow(dict(row, message=msg))

INPUT *input_file=/etc/irods/yoda-ruleset/tools/test_script.csv, *output_file=/etc/irods/yoda-ruleset/tools/result_script.csv, *run_type=repair, *dry_run=True
OUTPUT ruleExecOut 