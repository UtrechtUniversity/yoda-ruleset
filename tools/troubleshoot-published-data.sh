#!/bin/bash

# Usage function to display help for the script
usage() {
    echo "Usage: $0 [data_package_name]"
    echo "  data_package_name: Troubleshoot a specific data package by name"
    echo "  If no data package name is provided, all published data packages will be troubleshooted."
    echo "Example:"
    echo "  $0  # Troubleshoot all packages"
    echo "  $0 'research-core-0[1722266819]'  # Troubleshoot a specific package"
}

# Default package name to troubleshoot all published packages
data_package="all_published_packages"

# Check if a specific package name is provided as an argument
if [ -n "$1" ]; then
    if [[ "$1" == -* ]]; then
        echo "Invalid option: $1" 1>&2
        usage
        exit 1
    fi
    data_package="$1"
fi

# Execute the rule with the specified or all packages
/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/troubleshoot_data.r "*data_package=${data_package}"
