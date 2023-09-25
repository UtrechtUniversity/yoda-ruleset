#!/usr/bin/env python
"""This script cleans up data object revisions, by invoking the revision cleanup rules."""

import argparse
import atexit
import json
import os
import subprocess
import sys

NAME          = os.path.basename(sys.argv[0])
LOCKFILE_PATH = '/tmp/irods-{}.lock'.format(NAME)


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endofcalendarday", help="End of calendar day (epoch time)")
    parser.add_argument("bucketcase", choices=["A", "B", "Simple"], help="Bucket case configuration name")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of revisions to process at a time (default: 1).", required=False)
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Make the revision cleanup rules print additional information for troubleshooting purposes.")
    return parser.parse_args()


def lock_or_die():
    """Prevent running multiple instances of this job simultaneously"""

    # Create a lockfile for this job type, abort if it exists.
    try:
        fd = os.open(LOCKFILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        if os.path.exists(LOCKFILE_PATH):
            print('Not starting job: Lock file {} exists'.format(LOCKFILE_PATH))
            exit(1)
        else:
            raise
    os.write(fd, bytes(str(os.getpid()).encode("utf-8")))
    os.close(fd)

    # Remove lock no matter how we exit.
    atexit.register(lambda: os.unlink(LOCKFILE_PATH))


def clean_up(revisions, bucketcase, endofcalendarday, verbose_flag):
    chunk = json.dumps(revisions)
    chunk = "\\\\".join(chunk.split("\\"))
    chunk = "\\'".join(chunk.split("'"))
    return subprocess.check_output([
        'irule',
        '-r',
        'irods_rule_engine_plugin-irods_rule_language-instance',
        "*out=''; rule_revisions_clean_up('{}', '{}', '{}', '{}', *out); writeString('stdout', *out);".format(chunk, bucketcase, endofcalendarday, verbose_flag),
        'null',
        'ruleExecOut'
    ])


def get_revisions_info():
    return json.loads(subprocess.check_output([
        'irule',
        '-r',
        'irods_rule_engine_plugin-irods_rule_language-instance',
        '*out=""; rule_revisions_info(*out); writeString("stdout", *out);',
        'null',
        'ruleExecOut'
    ]))


def main():
    args = get_args()
    lock_or_die()
    revisions_info = get_revisions_info()

    if args.verbose:
        print('START cleaning up revision store')

    while len(revisions_info) > args.batch_size:
        if args.verbose:
            print("Clean up for " + str(revisions_info[:args.batch_size]))
        clean_up(revisions_info[:args.batch_size],
                 args.bucketcase,
                 args.endofcalendarday,
                 "1" if args.verbose else "0")
        revisions_info = revisions_info[args.batch_size:]

    if args.verbose:
        print('END cleaning up revision store')


if __name__ == "__main__":
    main()
