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
    """Generate CSV output from results"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    
    for package in sorted(results.keys()):
        row = [package] + [results[package].get(field, 'N/A') for field in HEADERS[1:]]
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8')

def generate_human_output(results):
    """Generate human-readable output from results"""
    output = []
    for package in sorted(results.keys()):
        res = results[package]
        section = [
            f"Results for: {package}",
            "Package passed all tests." if all(
                res.get(field, 'N/A') == 'Pass' 
                for field in HEADERS[1:]  # Skip Package
            ) else "Package FAILED one or more tests:"
        ]
        
        if "FAILED" in section[-1]:
            for field in HEADERS[1:]:  # Skip Package
                section.append(f"{field}: {res.get(field, 'N/A')}")
        
        output.append('\n'.join(section))
    
    return '\n\n'.join(output).encode('utf-8')

def main(rule_args, callback, rei):
    try:
        params = {
            'data_package': global_vars["*data_package"].strip('"'),
            'mode': global_vars["*mode"].strip('"').lower()
        }
        
        if params['mode'] not in ('human', 'csv'):
            raise ValueError("Invalid mode. Use 'human' or 'csv'")

        ret_val = callback.rule_batch_troubleshoot_published_data_packages(
            params['data_package'], "", "", "", params['mode'], ""
        )
        results = json.loads(ret_val["arguments"][5])

        output = generate_csv(results) if params['mode'] == 'csv' else generate_human_output(results)
        callback.writeLine("stdout", output)

    except Exception as e:
        callback.writeLine("stdout", f"Error: {str(e)}".encode('utf-8'))

INPUT *data_package="", *log_loc="", *offline="", *no_datacite="", *mode=""
OUTPUT ruleExecOut
