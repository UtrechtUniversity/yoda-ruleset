#!/usr/bin/env python3
"""This script takes CSV file as input and includes pre-existing SRAM groups to be migrated to non-SRAM groups.

This script should be run before SRAM external users sync so that the sync has accurate user information as input.

Example:
To migrate SRAM groups to non-SRAM groups:
python3 sram-migration-script.py -c non-sram -f sram-groups-to-non-sram.csv

To output the results in a log file:
python3 sram-migration-script.py -c non-sram -f sram-groups-to-non-sram.csv -l

To dry run the migration script:
python3 sram-migration-script.py -c non-sram -f sram-groups-to-non-sram.csv -d
"""
import argparse
import subprocess


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="sram-migration-script.py",
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-l", "--log-file",
        action='store_true',
        help="Write output to log file at /var/lib/irods/log/sram-migration.log"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action='store_true',
        help="Run the migration script in dry-run mode without making changes"
    )
    parser.add_argument(
        "-t", "--target-group-type",
        type=str,
        required=True,
        choices=['sram', 'non-sram'],
        help="Convert groups to either 'sram' or 'non-sram'"
    )
    parser.add_argument(
        "-f", "--file-name",
        type=str,
        required=True,
        help="Path to CSV file containing group names to be migrated"
    )
    return parser.parse_args()

def main():
    """Execute the SRAM migration rule."""
    args = parse_args()
    rule_name = "/etc/irods/yoda-ruleset/tools/sram/sram-migration.r"
    log_loc = f"*log_loc={args.log_file if args.log_file else ''}"
    dry_run = f"*dry_run={args.dry_run if args.dry_run else ''}"
    target_group_type = f"*target_group_type={args.target_group_type}"
    file_name = f"*file_name={args.file_name}"

    subprocess.call(['irule', '-r', 'irods_rule_engine_plugin-python-instance', '-F',
                    rule_name, log_loc, dry_run, target_group_type, file_name])

if __name__ == '__main__':
    main()
