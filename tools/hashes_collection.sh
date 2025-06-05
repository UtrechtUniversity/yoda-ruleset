#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

#Set of shell commands to hash the set of data objects and hierarchy in a collection
#to compare the content of 2 collections, update the shell variable COLLECTION and rerun the query line

#explanation:
#1. we select logical path and data object size for each data object within the collection tree
#2. only good replicas (status '1') of data objects are considered for the hash calculation.
#3. we select logical path for each subcollection within the collection tree
#4. we remove the prefix (collection name) so that the logical name starts within the collection (needed for comparison)
#5. we sort the pathnames (data objects and subcollections), using a locale that ensures all characters have a different sorting order

DETAILED=0
DEBUG=0

# Define the hash calculation version
VERSION="v2.0"

# Initialize COLLECTION to be empty. This script strictly expects COLLECTION
# to be provided as a command-line argument.
COLLECTION=""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --detailed) DETAILED=1 ;;
        --debug) DEBUG=1 ;;
        # The first positional argument found is taken as the COLLECTION.
        # This will override any existing environment variable for the script's internal use.
        *) COLLECTION="${arg%/}" ;;
    esac
done

# If COLLECTION is still empty after parsing arguments, it means it wasn't provided.
if [ -z "$COLLECTION" ]; then
   echo "Usage: bash $0 <collectionName> [--detailed] [--debug]" >&2
   echo "ERROR: Missing required collection name argument." >&2
   exit 1
fi

# Using ils -d to check for collection existence
if ! ils -d "${COLLECTION}" > /dev/null 2>&1; then
    echo "ERROR: iRODS collection '${COLLECTION}' does not exist or is inaccessible." >&2
    echo "Please verify the collection path and your iRODS environment." >&2
    exit 1
fi

TEMPFILE_DATE=$(date +%Y%m%d)
TEMPFILE="$(mktemp --tmpdir=/tmp "check_objects.${TEMPFILE_DATE}.XXXXX")" || { echo "ERROR: Failed to create temporary file for objects." >&2; exit 1; }
TEMPFOLDER="$(mktemp --tmpdir=/tmp "check_collections.${TEMPFILE_DATE}.XXXXX")" || { echo "ERROR: Failed to create temporary file for collections." >&2; exit 1; }
TEMPSORTED="$(mktemp --tmpdir=/tmp "check_sorted.${TEMPFILE_DATE}.XXXXX")" || { echo "ERROR: Failed to create temporary file for sorted output." >&2; exit 1; }

export TEMPFILE
export TEMPFOLDER
export TEMPSORTED

# Ensure temporary files are cleaned up on exit, unless DEBUG is enabled.
if [ "$DEBUG" -ne 1 ]; then
    trap 'rm -f "$TEMPFILE" "$TEMPFOLDER" "$TEMPSORTED"' EXIT
fi

# --- Query 1: Data objects within subcollections (good replicas)
iquest --no-page "%s/%s %s" "select COLL_NAME,DATA_NAME,DATA_SIZE where COLL_NAME like '${COLLECTION}/%' and DATA_REPL_STATUS = '1'" | grep -v '^CAT_NO_ROWS_FOUND' | cut -c"$((${#COLLECTION}+1))"- >"${TEMPFILE}"
IQUEST_STATUS=("${PIPESTATUS[@]}")

if [[ ${IQUEST_STATUS[0]} -ne 0 && ${IQUEST_STATUS[0]} -ne 1 ]]; then
    echo "ERROR: iquest query for data objects in subcollections failed with status ${IQUEST_STATUS[0]}." >&2
    exit 1
fi

# --- Query 2: Data objects directly within the collection (good replicas)
iquest --no-page "%s/%s %s" "select COLL_NAME,DATA_NAME,DATA_SIZE where COLL_NAME = '${COLLECTION}' and DATA_REPL_STATUS = '1'" | grep -v '^CAT_NO_ROWS_FOUND' | cut -c"$((${#COLLECTION}+1))"- >>"${TEMPFILE}"
IQUEST_STATUS=("${PIPESTATUS[@]}")

if [[ ${IQUEST_STATUS[0]} -ne 0 && ${IQUEST_STATUS[0]} -ne 1 ]]; then
    echo "ERROR: iquest query for data objects directly in collection failed with status ${IQUEST_STATUS[0]}." >&2
    exit 1
fi

# --- Query 3: Subcollections themselves
iquest --no-page "%s" "select COLL_NAME where COLL_NAME like '${COLLECTION}/%'" | grep -v '^CAT_NO_ROWS_FOUND' | cut -c"$((${#COLLECTION}+1))"- >"${TEMPFOLDER}"
IQUEST_STATUS=("${PIPESTATUS[@]}")

if [[ ${IQUEST_STATUS[0]} -ne 0 && ${IQUEST_STATUS[0]} -ne 1 ]]; then
    echo "ERROR: iquest query for subcollections failed with status ${IQUEST_STATUS[0]}." >&2
    exit 1
fi


cat "${TEMPFILE}" "${TEMPFOLDER}" | LC_ALL=C sort > "${TEMPSORTED}"
CHECKSUM=$(sha256sum "${TEMPSORTED}" | cut -f1 -d' ')

if [ "$DETAILED" -eq 1 ]; then
  echo "DATA MANIFEST"
  echo "-------------"
  echo "Manifest created on : $(date -u)"
  echo "Hash Method Version : ${VERSION}"
  echo "Content of directory: ${COLLECTION}"
  echo "File count          : $(wc -l <"${TEMPFILE}")"
  echo "Subdirectories count: $(wc -l <"${TEMPFOLDER}")"
  echo "Checksum            : ${CHECKSUM}"
  echo "-------------"
  echo " "
  echo "List of Subdirectories and Files (size in bytes)"
  echo "================================================"
  cat "${TEMPSORTED}"
else
  echo "${VERSION}:${CHECKSUM}"
fi

if [ "$DEBUG" -ne 1 ]; then
  rm -f "${TEMPFILE}" "${TEMPFOLDER}" "${TEMPSORTED}"
fi
