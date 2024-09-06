#!/usr/bin/env python3
"""This script collects all published packages and checks that they have all the required info.

Example:
To check all published packages:
python3 troubleshoot-published-data.py

To check one specific package by name:
python3 troubleshoot-published-data.py -p research-initial[1725262507]

To put results into a json lines log file:
python3 troubleshoot-published-data.py -l /etc/irods/yoda-ruleset/troubleshoot-pub-log.jsonl
"""
import argparse
import subprocess


def parse_args():
    parser = argparse.ArgumentParser(
        prog="troubleshoot-published-data.py",
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-l", "--log-file", type=str, required=False,
                        help="If write to json lines log file, location to write to")
    parser.add_argument("-p", "--package", type=str, required=False,
                        help="Troubleshoot a specific data package by name (default: troubleshoot all packages)")
    # TODO argument to optionally add an avu with json status info: time of check and was it a success
    return parser.parse_args()


def main():
    args = parse_args()
    rule_name = "/etc/irods/yoda-ruleset/tools/troubleshoot_data.r"
    data_package = f"*data_package={args.package}"
    log_loc = f"*log_loc={args.log_file if args.log_file else ''}"
    subprocess.call(['irule', '-r', 'irods_rule_engine_plugin-python-instance', '-F',
                    rule_name, data_package, log_loc])


if __name__ == '__main__':
    main()
