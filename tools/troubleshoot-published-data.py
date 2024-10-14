#!/usr/bin/env python3
"""This script collects all published packages and checks that they have all the required info.

Example:
To check all published packages:
python3 troubleshoot-published-data.py

To check one specific package by name:
python3 troubleshoot-published-data.py -p research-initial[1725262507]

To put results into a log file and complete the checks offline:
python3 troubleshoot-published-data.py -l -o
"""
import argparse
import subprocess


def parse_args():
    parser = argparse.ArgumentParser(
        prog="troubleshoot-published-data.py",
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-l", "--log-file", action='store_true',
                        help="If log file parameter is true then write to log at: /var/lib/irods/log/troubleshoot_publications.log")
    parser.add_argument("-o", "--offline", action='store_true',
                        help="If actions should be performed without connecting to external servers (needed for the Yoda team's development setup).")
    parser.add_argument("-p", "--package", type=str, required=False,
                        help="Troubleshoot a specific data package by name (default: troubleshoot all packages)")
    return parser.parse_args()


def main():
    args = parse_args()
    rule_name = "/etc/irods/yoda-ruleset/tools/troubleshoot_data.r"
    data_package = f"*data_package={args.package}"
    log_loc = f"*log_loc={args.log_file if args.log_file else ''}"
    offline = f"*offline={args.offline}"
    subprocess.call(['irule', '-r', 'irods_rule_engine_plugin-python-instance', '-F',
                    rule_name, data_package, log_loc, offline])


if __name__ == '__main__':
    main()
