#!/bin/bash
#
# This script runs the integration tests, or a subset of them.
#
# Run all tests:                    ./run-integration-tests.sh
# Run tests with a specific prefix: ./run-integration-tests.sh util.collection.*
# Run one specific test:            ./run-integration-test.ssh util.collection.owner


TESTS="$1"
TOOLSDIR=$(dirname "$0")
/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F "$TOOLSDIR/run-integration-tests.r" "$TESTS"
