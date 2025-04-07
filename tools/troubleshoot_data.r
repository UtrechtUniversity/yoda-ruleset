#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F

import csv
import io
import json

HEADERS = [
    "Package", 
    "Schema Check",
    "Missing AVUs Check",
    "Unexpected AVUs Check",
    "Version DOI Check",
    "Base DOI Check",
    "Landing Page Check",
    "Combi JSON Check"
]

def generate_csv(results):
    """Generate CSV output from troubleshooting results"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    
    for package in sorted(results.keys()):
        res = results[package]
        row = [package]
        for field in HEADERS[1:]:
            # Get value or N/A if missing
            value = res.get(field, 'N/A')
            row.append(str(value) if value not in ('Pass', 'Fail') else value)
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8')

def generate_human_output(results):
    """Generate human-readable output from troubleshooting results"""
    output = []
    for package in sorted(results.keys()):
        res = results[package]
        present_fields = [field for field in HEADERS[1:] if field in res]
        
        status_line = (
            "Package passed all tests." 
            if all(res[field] == 'Pass' for field in present_fields) 
            else "Package FAILED one or more tests:"
        )
        
        section = [
            f"Results for: {package}",
            status_line
        ]
        
        if "FAILED" in status_line:
            for field in present_fields:
                section.append(f"{field}: {res[field]}")
        
        output.append('\n'.join(section))
    
    return '\n\n'.join(output).encode('utf-8')

def main(rule_args, callback, rei):
    params = {
        'data_package': global_vars["*data_package"].strip('"'),
        'log_loc': global_vars["*log_loc"].strip('"'),
        'offline': global_vars["*offline"].strip('"'),
        'no_datacite': global_vars["*no_datacite"].strip('"'),
        'mode': global_vars["*mode"].strip('"').lower()
    }
    
    # Validate mode before proceeding
    if params['mode'] not in ('human', 'csv'):
        raise ValueError("Invalid mode. Use 'human' or 'csv'")

    # Execute troubleshooting with all parameters
    ret_val = callback.rule_batch_troubleshoot_published_data_packages(
        params['data_package'],
        params['log_loc'],
        params['offline'],
        params['no_datacite'],
        params['mode'],
        ""  # Output placeholder
    )
    
    # Process and output results
    results = json.loads(ret_val["arguments"][5])
    output = generate_csv(results) if params['mode'] == 'csv' else generate_human_output(results)
    callback.writeLine("stdout", output)


INPUT *data_package="", *log_loc="", *offline="", *no_datacite="", *mode=""
OUTPUT ruleExecOut
