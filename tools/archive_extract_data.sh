#!/bin/bash
###############################################################################
# archive_extract_data_collection.sh
#
# Script for archiving or extracting data in iRODS using iRODS rules.
# Provides two modes:
#   1) Archive a source collection to a single archive file (.tar, .zip, etc.)
#   2) Extract an existing archive file into a specified folder
#
# This script relies on msiArchiveCreate and msiArchiveExtract via 'irule'.
#
# Usage:
#   1) ARCHIVE mode example:
#      ./archive_extract_data_collection.sh \
#        -mode archive \
#        -s /tempZone/home/research-initial/data-package-dylan \
#        -a /tempZone/home/research-initial/archives/backup.tar \
#        -r myResource
#
#   2) EXTRACT mode example:
#      ./archive_extract_data_collection.sh \
#        -mode extract \
#        -A /tempZone/home/research-initial/backup.tar \
#        -t /tempZone/home/research-initial/extract \
#        -e null \
#        -r myResource
#
# For extracting a single file from an archive, specify the sub-file in the archive:
#   -e /path/inside/archive
# If you want to extract the entire archive, use: -e null
#
###############################################################################

DEFAULT_RULE_ENGINE="irods_rule_engine_plugin-irods_rule_language-instance"

###############################################################################
# Display script usage
###############################################################################
usage() {
    cat <<EOF
Usage:
  $0 -mode <archive|extract> [options]

Modes:
  archive   Archive data from a source collection into a single archive file
  extract   Extract data from an existing archive into a target collection

Common Options (depending on mode):
  -r, --target-resource    Target iRODS storage resource (default: null)
  -h, --help               Show this help message

Archive Mode Options:
  -s, --source-collection  Full iRODS path to source collection (required)
  -a, --archive-target     Full iRODS path for archive output (e.g., .tar or .zip)

Extract Mode Options:
  -A, --archive-path       Full iRODS path to the existing archive file
  -t, --target-collection  Full iRODS path where data should be extracted
  -e, --extract-file       Path of a single file/folder inside the archive to extract
                           (default: null for entire archive)

Examples:
  1) Archive Mode:
     $0 -mode archive -s /tempZone/home/research-initial/myData \
        -a /tempZone/home/research-initial/archives/myArchive.tar \
        -r myResource

  2) Extract Mode:
     $0 -mode extract -A /tempZone/home/research-initial/myArchive.tar \
        -t /tempZone/home/research-initial/myExtractedData \
        -e null \
        -r myResource

EOF
}

###############################################################################
# Validate arguments for ARCHIVE mode
###############################################################################
validate_archive_arguments() {
    local errors=0

    if [[ -z "$source_collection" ]]; then
        echo "ERROR: Source collection is required for archive mode" >&2
        errors=$((errors+1))
    fi
    if [[ -z "$archive_target_path" ]]; then
        echo "ERROR: Archive target path is required for archive mode" >&2
        errors=$((errors+1))
    fi

    # Normalize paths for defensive check
    local normalized_source="${source_collection%/}"
    local normalized_target_parent="${archive_target_path%/*}"  # parent directory path

    # Check if target is inside source collection
    if [[ "$normalized_target_parent" == "$normalized_source"* ]]; then
        cat <<EOF >&2
ERROR: Archive target cannot be inside source collection!
  Source: $normalized_source
  Target: $archive_target_path

This would cause recursive archiving and is not permitted.
EOF
        errors=$((errors+1))
    fi

    return $errors
}

###############################################################################
# Validate arguments for EXTRACT mode
###############################################################################
validate_extract_arguments() {
    local errors=0

    if [[ -z "$archive_path" ]]; then
        echo "ERROR: Archive path (-A) is required for extract mode" >&2
        errors=$((errors+1))
    fi
    if [[ -z "$extract_path" ]]; then
        echo "ERROR: Target collection (-t) is required for extract mode" >&2
        errors=$((errors+1))
    fi

    return $errors
}

###############################################################################
# Parse command-line arguments
###############################################################################
mode=""
source_collection=""
archive_target_path=""
archive_path=""
extract_path=""
extract_file=""
target_resource="null"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -mode)
            mode="$2"
            shift 2
            ;;
        -s|--source-collection)
            source_collection="$2"
            shift 2
            ;;
        -a|--archive-target)
            archive_target_path="$2"
            shift 2
            ;;
        -A|--archive-path)
            archive_path="$2"
            shift 2
            ;;
        -t|--target-collection)
            extract_path="$2"
            shift 2
            ;;
        -e|--extract-file)
            extract_file="$2"
            shift 2
            ;;
        -r|--target-resource)
            target_resource="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Invalid option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

###############################################################################
# Validate mode
###############################################################################
if [[ -z "$mode" ]]; then
    echo "ERROR: -mode <archive|extract> is required" >&2
    usage
    exit 1
fi

if [[ "$mode" != "archive" && "$mode" != "extract" ]]; then
    echo "ERROR: Unknown mode '$mode'. Use 'archive' or 'extract'." >&2
    usage
    exit 1
fi

###############################################################################
# Validate arguments based on mode
###############################################################################
if [[ "$mode" == "archive" ]]; then
    validate_archive_arguments || exit 1
else
    # Default to "null" if extract_file not specified
    if [[ -z "$extract_file" ]]; then
        extract_file="null"
    fi
    validate_extract_arguments || exit 1
fi

###############################################################################
# Helper function for showing elapsed time during operation
###############################################################################
elapsed_time() {
    local start=$1
    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start))
        printf "\rElapsed time: %02d:%02d:%02d (refresh every 10s)" \
               $((elapsed/3600)) $(((elapsed%3600)/60)) $((elapsed%60))
        sleep 10
    done
}

###############################################################################
# Main operation (ARCHIVE or EXTRACT)
###############################################################################
TEMP_OUTPUT=$(mktemp)
start_time=$(date +%s)

echo "-----------------------------------------------------"
echo "Starting operation in '$mode' mode."
echo "Target resource: $target_resource"
echo "-----------------------------------------------------"

###############################################################################
# Start elapsed time monitoring
###############################################################################
elapsed_time "$start_time" &
timer_pid=$!

###############################################################################
# Execute either ARCHIVE or EXTRACT
###############################################################################
if [[ "$mode" == "archive" ]]; then
    echo "Archiving collection..."
    echo "  Source collection:  $source_collection"
    echo "  Archive file path:  $archive_target_path"

    irule -r "$DEFAULT_RULE_ENGINE" \
        "msiArchiveCreate(*archiveTargetPath, *sourceCollection, *targetResource, *status=0)" \
        "*archiveTargetPath=$archive_target_path%*sourceCollection=$source_collection%*targetResource=$target_resource%*status=0" \
        ruleExecOut > "$TEMP_OUTPUT" 2>&1
    exit_code=$?

else
    echo "Extracting archive..."
    echo "  Archive file path:  $archive_path"
    echo "  Extract to path:    $extract_path"
    echo "  Extract file:       $extract_file (use 'null' for full archive)"

    irule -r "$DEFAULT_RULE_ENGINE" \
        "msiArchiveExtract(*archivePath, *extractPath, *extractFile, *targetResource, *status=0)" \
        "*archivePath=$archive_path%*extractPath=$extract_path%*extractFile=$extract_file%*targetResource=$target_resource%*status=0" \
        ruleExecOut > "$TEMP_OUTPUT" 2>&1
    exit_code=$?
fi

###############################################################################
# Stop elapsed timer, display output, handle errors
###############################################################################
kill "$timer_pid" 2>/dev/null
echo ""
irule_output=$(cat "$TEMP_OUTPUT")
rm -f "$TEMP_OUTPUT"

if [[ $exit_code -ne 0 ]]; then
    cat <<EOF

ERROR: Operation failed (mode: $mode)
Exit code: $exit_code
Rule output:
$irule_output

Troubleshooting tips:
  1. Verify the iRODS paths exist:
  2. Check that the parent directory exists for the target path.
  3. Confirm permissions on both source and target paths.
EOF
    exit $exit_code
else
    cat <<EOF

SUCCESS! mode: $mode
Rule output:
$irule_output
EOF
fi
