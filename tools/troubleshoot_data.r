#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

import csv
import io
import json

def main(rule_args, callback, rei):
    # Read input parameters
    data_package = global_vars["*data_package"].strip('"')
    log_loc = global_vars["*log_loc"].strip('"')
    offline = global_vars["*offline"].strip('"')
    no_datacite = global_vars["*no_datacite"].strip('"')
    mode = global_vars["*mode"].strip('"')
    #callback.writeLine("stdout", mode.encode('utf-8'))

    # Pass all parameters to Python rule
    ret_val = callback.rule_batch_troubleshoot_published_data_packages(
        data_package,
        log_loc,
        offline,
        no_datacite,
        mode,
        "" 
    )
    
    results = json.loads(ret_val["arguments"][5])

    # Create text buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV header
    writer.writerow([
        "Package", 
        "Schema Check",
        "Missing AVUs Check",
        "Unexpected AVUs Check",
        "Version DOI Check",
        "Base DOI Check",
        "Landing Page Check",
        "Combi JSON Check"
    ])
    callback.writeLine("stdout", output.getvalue().strip().encode('utf-8'))
    output.seek(0)
    output.truncate()

    # Write CSV rows
    for package in sorted(results.keys()):
        res = results[package]
        writer.writerow([
            package,
            res.get('schema_check', 'N/A'),
            res.get('no_missing_AVUs_check', 'N/A'),
            res.get('no_unexpected_AVUs_check', 'N/A'),
            res.get('versionDOI_check', 'N/A'),
            res.get('baseDOI_check', 'N/A'),
            res.get('landingPage_check', 'N/A'),
            res.get('combiJson_check', 'N/A')
        ])
        callback.writeLine("stdout", output.getvalue().strip().encode('utf-8'))
        output.seek(0)
        output.truncate()

INPUT *data_package="", *log_loc="", *offline="", *no_datacite="", *mode=""
OUTPUT ruleExecOut
