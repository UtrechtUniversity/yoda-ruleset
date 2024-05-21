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
    except RuntimeError as e:
        callback.writeLine("stdout","[msi_stat_vault failed on path '{}' with error - '{}'".format(data_path, errorcode(e)))
        return -1, "[msi_stat_vault failed on path '{}' with error - '{}'".format(data_path, errorcode(e))

    return type, size

def preconditions_for_data_object(data, callback):

    replicas_list = []

    # Check if file exists in the current data path
    actual_file_type, actual_file_size = data_file_exists(data['resc_name'], data['actual_datapath'], callback)

    if actual_file_type == 'NOTEXIST':
        expected_type, expected_size = data_file_exists(data['resc_name'], data['expected_datapath'], callback)

        if expected_type == 'FILE':
            # Count other replicas with same data path
            expected_iter = genquery.row_iterator(
            "DATA_ID, DATA_REPL_NUM, RESC_NAME, RESC_LOC", 
            "DATA_PATH = '{}'".format(data['expected_datapath']),
            genquery.AS_LIST,
            callback)

            for row in expected_iter:
                if row[0] != data['data_id']:
                    replicas_list.append(row[0])

            if len(replicas_list) == 0:
                callback.writeLine("stdout", "Expected data path is not used by other replicas.")

                # The data file should pass compatibility check with the replica
                actual_iter = genquery.row_iterator(
                "DATA_SIZE, DATA_CHECKSUM, RESC_LOC",
                "DATA_ID ='{}' AND DATA_REPL_NUM = '{}'".format(data['data_id'], data['data_repl_num']),
                genquery.AS_TUPLE,
                callback)

                for row in actual_iter:
                    actual_size = row[0]
                    actual_chksum = row[1]

                if expected_size == actual_size:
                    callback.writeLine("stdout", "The replica and data file are compatible by size.")

                    #  Calculate checksum of replica if it is not registered and then compare it to data file checksum.
                    if not actual_chksum:
                        try:
                            chksum_output = callback.msi_file_checksum(data['actual_datapath'], data['resc_name'], '')
                            actual_chksum = chksum_output['arguments'][2]
                        except RuntimeError as e:
                            callback.writeLine("stdout","msi_file_checksum failed on path '{}' with error - '{}'".format(data['actual_datapath'], errorcode(e)))
                            return -1, "msi_file_checksum failed on path '{}' with error - '{}'".format(data['actual_datapath'], errorcode(e))
                    
                    try:
                        chksum_output = callback.msi_file_checksum(data['expected_datapath'], data['resc_name'], '')
                        expected_chksum = chksum_output['arguments'][2]
                    except RuntimeError as e:
                        callback.writeLine("stdout","msi_file_checksum failed on path '{}' with error - '{}'".format(data['expected_datapath'], errorcode(e)))
                        return -1, "msi_file_checksum failed on path '{}' with error - '{}'".format(data['expected_datapath'], errorcode(e))

                    if expected_chksum == actual_chksum:
                        callback.writeLine("stdout", "The checksum of replica and data file matches.")

                        # Modify data object
                        status = modify_data_object(data, callback)
                        if status == '':
                            return 0, status
                        else:
                            return -1, status

                    else:
                        return -1, "preconditions_for_data_object: Checksum of data file does not match with the replica."
                else:
                    return -1, "preconditions_for_data_object: The data file and replica are not compatible."
            else:
                return -1, "preconditions_for_data_object: Expected data path is in use by other replicas."
        else:
            return -1, "preconditions_for_data_object: Data file does not exist in the expected location."
    else:
        return -1, "preconditions_for_data_object: Actual file exists in the current data path."
        

def modify_data_object(data, callback):
    # Modify the replica with correct data path
    status = subprocess.check_output(['iadmin', 'modrepl', 'data_id', data['data_id'], 'replica_number', data['data_repl_num'], 'DATA_PATH', data['expected_datapath']], stderr=subprocess.STDOUT)
    return str(status)


def main(rule_args, callback, rei):

    file = global_vars["*file"]
    # Read CSV
    with open(file, 'r') as csvfile, open('/etc/irods/yoda-ruleset/tools/result_1.csv', 'w') as result:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames + ['message']
        writer = csv.DictWriter(result, fieldnames)
        writer.writeheader()

        for row in reader:
            row['resc_name'] = row['resc_name'].strip('\'')
            row['expected_datapath'] = row['expected_datapath'].strip('\'')
            row['actual_datapath'] = row['actual_datapath'].strip('\'')
            print(row['data_id'])
            if row['processed'] in ('ERROR', 'NO'):
                retCode, msg = preconditions_for_data_object(row, callback)
                if retCode == 0:
                    msg = 'Success'
                    row['processed'] = 'YES'
                    writer.writerow(dict(row, message=msg))
                else:
                    callback.writeLine("stdout", "Status: " + msg)
                    row['processed'] = 'ERROR'
                    writer.writerow(dict(row, message=msg))

INPUT *file=/etc/irods/yoda-ruleset/tools/test_1.csv
OUTPUT ruleExecOut 