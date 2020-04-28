#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import atexit

# usage: ./async-data-replicate.py

# This script handles both batch replication and batch creation of revisions,
# depending on by which name it is called.
#
# (the revision rule currently does not exist)

NAME          = os.path.basename(sys.argv[0])
LOCKFILE_PATH = '/tmp/irods-{}.lock'.format(NAME)

def lock_or_die():
    """Prevent running multiple instances of this job simultaneously"""

    # Create a lockfile, abort if it exists.
    try:
        fd = os.open(LOCKFILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        if os.path.exists(LOCKFILE_PATH):
            print('error: Lock file {} exists'.format(LOCKFILE_PATH), file=sys.stderr)
            exit(1)
        else:
            raise
    os.write(fd, str(os.getpid()))
    os.close(fd)

    # Remove lock no matter how we exit.
    atexit.register(lambda: os.unlink(LOCKFILE_PATH))

if 'replicate' in NAME:
    rule_name = 'uuReplicateBatch'
elif 'revision' in NAME:
    rule_name = 'uuRevisionBatch'
else:
    print('bad command "{}"'.format(NAME), file=sys.stderr)
    exit(1)

lock_or_die()

import subprocess

subprocess.call(['irule', rule_name+'()', 'null', 'ruleExecOut'])
