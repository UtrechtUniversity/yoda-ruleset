#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import subprocess
import sys
import atexit


print("BLBLB")

rule_name = 'rule_harm()'

# args = get_args()

rule_options = '{"ctx": "ctx", "verbose": "1"}'

# subprocess.call(['irule', '-r', 'irods_rule_engine_plugin-irods_rule_language-instance',
#    rule_name, rule_options, 'ruleExecOut'])


subprocess.call(['irule', '-r', 'irods_rule_engine_plugin-python-instance', 'rule_harm', rule_options, ''])

print("en er weer uit")
