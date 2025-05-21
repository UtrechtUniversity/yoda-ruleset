#!/bin/bash
# set of shell commands to hash the set of data objects and hierarchy in a collection
# To compare the content of 2 collections, update the shell variable COLLECTION and rerun the query line
# explanation:
# 1. we select logical path and data object size for each data object within the collection tree
# 2. we remove the prefix (collection name) so that the logical name starts within the collection (needed for comparison)
# 3. we sort the pathnames, using a locale that ensures all characters have a different sorting order
# bash commands:

# Check if COLLECTION argument is provided
if [ -z "$1" ]; then
    echo "Error: Collection path must be provided as an argument." >&2
    echo "Usage: $0 <collection-path>" >&2
    exit 1
fi

COLLECTION="${1%/}/"
iquest --no-page "%s/%s %s" "select COLL_NAME,DATA_NAME,DATA_SIZE where COLL_NAME like '${COLLECTION}%'"|cut -c$((${#COLLECTION}+1))-|LC_ALL=C sort|sha256sum
