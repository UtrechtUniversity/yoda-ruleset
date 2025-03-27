#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

#TODO: WHy use bytesIO not stringIO
# Save to a CSV file or output in CSV? If to a file, any example?
import csv
import io
import json

def main(rule_args, callback, rei): # TODO: Shall we Use rule_args? 
    # Read input parameters
    data_package = global_vars["*data_package"].strip('"')
    log_loc = global_vars["*log_loc"].strip('"')
    offline = global_vars["*offline"].strip('"')
    no_datacite = global_vars["*no_datacite"].strip('"')

    # Get raw JSON results from Python rule
    ret_val = callback.rule_batch_troubleshoot_published_data_packages(
        data_package,
        log_loc,
        offline,
        no_datacite,
        ""
    )
    results = json.loads(ret_val["arguments"][4])
    callback.writeLine("stdout log_loc", log_loc.encode('utf-8'))
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
            str(res.get('schema_check', 'N/A')),
            str(res.get('no_missing_AVUs_check', 'N/A')),
            str(res.get('no_unexpected_AVUs_check', 'N/A')),
            str(res.get('versionDOI_check', 'N/A')),
            str(res.get('baseDOI_check', 'N/A')),
            str(res.get('landingPage_check', 'N/A')),
            str(res.get('combiJson_check', 'N/A'))
        ])
        callback.writeLine("stdout", output.getvalue().strip().encode('utf-8'))
        output.seek(0)
        output.truncate()
    # return CSV format # TODO: Check with Sietse: Flag to CSV or readable formats # Example: Irods consistency checker 
    # TODO: Remove path (only keeping the package name in CSV output)
    # TODO: check with sietse: use Pass or Fail # Use it for both readable and CSV output
INPUT *data_package="", *log_loc="", *offline="", *no_datacite=""
OUTPUT ruleExecOut
