#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# This script modifies the data objects listed in CSV file.
# 
import subprocess
import genquery
import session_vars
import csv
import os.path

def data_file_exists(resc_name, data_path, callback):
    # Verify that data file exists in given data path
    output = callback.msi_stat_vault(resc_name, data_path, "", "")
    return output['arguments'][2], output['arguments'][3]


def preconditions_for_data_object(data, zone, callback):

    replicas_list = []

    # Check if file exists in the current data path
    actual_file_type, actual_file_size = data_file_exists(data[1], data[3], callback)

    if actual_file_type == 'NOTEXIST':
        expected_type, expected_size = data_file_exists(data[1], data[4], callback)

        if expected_type == 'FILE':
            # Count other replicas with same data path
            expected_iter = genquery.row_iterator(
            "DATA_ID, DATA_REPL_NUM, RESC_NAME, RESC_LOC", 
            "USER_ZONE = '{}' AND DATA_PATH = '{}'".format(zone, data[4]),
            genquery.AS_LIST,
            callback)

            for row in expected_iter:
                if row[0] != data[0]:
                    replicas_list.append(row[0])

            if len(replicas_list) == 0:
                callback.writeLine("stdout", "Expected data path is not used by other replicas.")

                # The data file should pass compatibility check with the replica
                actual_iter = genquery.row_iterator(
                "DATA_SIZE, DATA_CHECKSUM, RESC_LOC",
                "USER_ZONE = '{}' AND DATA_ID ='{}' AND DATA_REPL_NUM = '{}'".format(zone, data[0], data[2]),
                genquery.AS_TUPLE,
                callback)

                for row in actual_iter:
                    actual_size = row[0]
                    actual_chksum = row[1]

                if expected_size == actual_size:
                    callback.writeLine("stdout", "The replica and data file are compatible by size.")

                    #  Calculate checksum of data file if replica checksum is registered.
                    if actual_chksum:
                        chksum_output = callback.msi_file_checksum(data[4], data[1], '')
                        expected_chksum = chksum_output['arguments'][2]

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
    status = subprocess.check_output(['iadmin', 'modrepl', 'data_id', data[0], 'replica_number', data[2], 'DATA_PATH', data[4]], stderr=subprocess.STDOUT)
    return str(status)


def main(rule_args, callback, rei):
    zone = session_vars.get_map(rei)['client_user']['irods_zone']
    file = global_vars["*file"]
    # Read CSV
    with open(file, 'r') as csvfile, open('/etc/irods/yoda-ruleset/tools/result.csv', 'w') as result:
        reader = csv.reader(csvfile, delimiter=';')
        writer = csv.writer(result, delimiter=';')

        header = reader.next()
        writer.writerow(header)

        for row in reader:
            if row[5] in ('ERROR', 'NO'):
                retCode, msg = preconditions_for_data_object(row, zone, callback)
                if retCode == 0:
                    row[5] = 'YES'
                    writer.writerow(row)
                else:
                    callback.writeLine("stdout", msg)
                    row[5] = 'ERROR'
                    writer.writerow(row)

INPUT *file=/etc/irods/yoda-ruleset/tools/test.csv
OUTPUT ruleExecOut 