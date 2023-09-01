#!/usr/bin/env python

import json
import subprocess
import sys


if len(sys.argv) != 3:
    print('Usage: {} endOfCalendarDay bucketcase'.format(sys.argv[0]))
    exit(1)

endOfCalendarDay = sys.argv[1]
bucketcase       = sys.argv[2]


def clean_up(revisions):
    chunk = json.dumps(revisions)
    chunk = "\\\\".join(chunk.split("\\"))
    chunk = "\\'".join(chunk.split("'"))
    return subprocess.check_output([
        'irule',
        '-r',
        'irods_rule_engine_plugin-irods_rule_language-instance',
        "*out=''; rule_revisions_clean_up('{}', '{}', '{}', *out); writeString('stdout', *out);".format(chunk, bucketcase, endOfCalendarDay),
        'null',
        'ruleExecOut'
    ])


print('START cleaning up revision store')

revisions_info = json.loads(subprocess.check_output([
    'irule',
    '-r',
    'irods_rule_engine_plugin-irods_rule_language-instance',
    '*out=""; rule_revisions_info(*out); writeString("stdout", *out);',
    'null',
    'ruleExecOut'
]))

while len(revisions_info) > 100:
    clean_up(revisions_info[:100])
    revisions_info = revisions_info[100:]
print(clean_up(revisions_info))
