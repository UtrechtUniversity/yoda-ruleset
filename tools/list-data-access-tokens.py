#!/usr/bin/env python

""" This script lists all data access tokens, or all data access token of a specific user."""

import argparse
import csv
from datetime import datetime
import os.path
import re
import sys

try:
    from pysqlcipher3 import dbapi2 as sqlite3
except ImportError, e:
    exit_with_error("Error: pysqlcipher3 not available. It should have been installed by the Yoda playbook.")


def exit_with_error(message):
    print >> sys.stderr, message
    sys.exit(1)


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user", default=None, nargs='?', help="User to search for (optional)")
    parser.add_argument("-n", "--name-only", action='store_true',
                        help="Only display user names, no token information")
    parser.add_argument("-m", "--format", default='human',
                        help="Output format", choices=['human', 'csv'])
    return parser.parse_args()


def read_dap_config():
    config_file = "/etc/irods/yoda-ruleset/rules_uu.cfg"

    if not os.path.isfile(config_file):
        exit_with_error("Error: cannot find ruleset config file.")

    token_database = None
    token_database_password = None

    with open(config_file, "r") as config:
        for line in config:
            td_match = re.search(r"^token_database\s+=\s+\'(\S+)\'", line)
            tdp_match = re.search(r"^token_database_password\s+=\s+\'(\S+)\'", line)
            if td_match:
                token_database = td_match.group(1)
            elif tdp_match:
                token_database_password = tdp_match.group(1)

    return (token_database, token_database_password)


def get_tokens(token_database, token_database_password, user=None):
    if not os.path.isfile(token_database):
        exit_with_error("Error: cannot find token database")

    conn = sqlite3.connect(token_database)
    result = []

    with conn:
        conn.execute("PRAGMA key='%s'" % (token_database_password))
        if user is None:
            dbdata = conn.execute('SELECT user, label, exp_time FROM tokens')
        else:
            dbdata = conn.execute('SELECT user, label, exp_time FROM TOKENS WHERE user=:user_id',
                                  {'user_id': user})

        for row in dbdata:
            exp_time = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S.%f')
            exp_time = exp_time.strftime('%Y-%m-%d %H:%M:%S')
            result.append({"user": row[0], "label": row[1], "exp_time": exp_time})

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually
    conn.close()

    return result


def print_tokens(data, args):
    if args.name_only:
        usernames = sorted(list(set(map(lambda d: d["user"], data))))
        for username in usernames:
            print(username)
    else:
        sorted_data = sorted(data, key=lambda d: d["user"])
        fieldnames = ["user", "label", "exp_time"]
        if args.format == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            for token in sorted_data:
                writer.writerow(token)
        elif args.format == "human":
            for token in sorted_data:
                print('{0:40} {1:19} {2:19}'.format(
                     token["user"],
                     token["label"],
                     token["exp_time"]))
        else:
            exit_with_error("Error: unknown output format")


def main():
    args = get_args()
    (token_database, token_database_password) = read_dap_config()
    data = get_tokens(token_database, token_database_password, args.user)
    print_tokens(data, args)


if __name__ == "__main__":
    main()
