#!/bin/bash

# Command to execute
# TODO: Add option to trouble shoot a single data package
# TODO: Assuming AVUs = schema-avus/yoda-metadata avus + system metadata avus
# where schema-avus/yoda-metadata avus is derived from schema keys
# where system metadata avus is derived from a ground-truth data package

# Logics:
# 1. for an example package: '/tempZone/home/vault-default-3/research-default-3[1722327809]'
# 2. for schema-avus, check if all schema-avus match keys in target schema_id
# 3. for system-avus, check if all system-avus match keys of the ground-truth data package
# 4. print out the result
