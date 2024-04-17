#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# This script modifies the data objects listed in CSV file.
# 
import subprocess
import csv
import os.path

def modify_data_object(data, callback):

    if not os.path.exists(data[2]):
        callback.writeLine("stdout", "Error: The path does not exist.")

    if not os.path.isfile(data[2]):
        callback.writeLine("stdout", "Error: The file does not exist in path.")

    subprocess.call(['iadmin', 'modrepl', 'data_id', data[0], 'replica_number', data[1], 'DATA_PATH', data[3]])


def main(rule_args, callback, rei):
    file = global_vars["*file"]
    # Read CSV
    with open(file, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        reader.next()
        for row in reader:
            modify_data_object(row, callback)

INPUT *file=/etc/irods/yoda-ruleset/tools/test.csv
OUTPUT ruleExecOut 