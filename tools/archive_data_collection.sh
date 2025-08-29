#!/bin/bash
###############################################################################
# Archive Data Collection Script
# 
# Archives a given iRODS collection to an archive file within iRODS 
# Using msiArchiveCreate.
###############################################################################

DEFAULT_RULE_ENGINE="irods_rule_engine_plugin-irods_rule_language-instance"

# Helper function
usage() {
    cat <<EOF
Archive an iRODS data collection to a single file using rule-based archiving.

Important Safety Check: 
  The archive target cannot be located within the source collection.

Usage: $0 -s SOURCE_COLLECTION -a ARCHIVE_TARGET_PATH [-r TARGET_RESOURCE]

Required Arguments:
  -s, --source-collection    Full iRODS path to source collection
  -a, --archive-target-path  Full iRODS path for archive output (.tar file suggested)

Optional Arguments:
  -r, --target-resource      Target iRODS storage resource (default: none)
  -h, --help                 Show this help message

Example:
  $0 -s /tempZone/home/research-initial/data-package-dylan \\
     -a /tempZone/home/research-initial/archives/backup.tar
EOF
}

# Validate required arguments
validate_arguments() {
    local errors=0
    
    if [[ -z "$source_collection" ]]; then
        echo "ERROR: Source collection is required" >&2
        errors=$((errors+1))
    fi
    
    if [[ -z "$archive_target_path" ]]; then
        echo "ERROR: Archive target path is required" >&2
        errors=$((errors+1))
    fi
    
    # Normalize paths for defensive check
    local normalized_source="${source_collection%/}"
    local normalized_target="${archive_target_path%/*}"  # Get parent path
    
    # Check if target is inside source collection
    if [[ "$normalized_target" == "$normalized_source"* ]]; then
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

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--source-collection)
            source_collection="$2"
            shift 2
            ;;
        -a|--archive-target-path)
            archive_target_path="$2"
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

# Validate inputs
validate_arguments || exit 1

# Execute archiving rule
echo "Starting archive creation:"
echo "  Source: $source_collection"
echo "  Target: $archive_target_path"
[[ -n "$target_resource" ]] && echo "  Resource: $target_resource"

# Create temp file for output capture
TEMP_OUTPUT=$(mktemp)

# Function to display elapsed time
elapsed_time() {
    local start=$1
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start))
        printf "\rElapsed time: %02d:%02d:%02d" \
               $((elapsed/3600)) $(((elapsed%3600)/60)) $((elapsed%60))
        sleep 1
    done
}

# Capture rule execution output and time the operation
start_time=$(date +%s)

# Start elapsed time counter in background
elapsed_time "$start_time" &
timer_pid=$!

# Execute rule and capture output
irule -r "$DEFAULT_RULE_ENGINE" \
    'msiArchiveCreate(*archiveTargetPath, *sourceCollection, *targetResource, *status=0)' \
    "*archiveTargetPath=$archive_target_path%*sourceCollection=$source_collection%*targetResource=$target_resource%*status=0" \
    'ruleExecOut' > "$TEMP_OUTPUT" 2>&1
exit_code=$?

# Stop and clean up the timer
kill $timer_pid 2>/dev/null
printf "\n"  # Move to new line after timer output

# Read captured output
irule_output=$(cat "$TEMP_OUTPUT")
rm -f "$TEMP_OUTPUT"

# Check execution status
if [[ $exit_code -ne 0 ]]; then
    cat <<EOF

ERROR: Archive creation failed
Exit code: $exit_code
Rule output:
$irule_output

Troubleshooting:
1. Verify source collection exists: ils '$source_collection'
2. Check target's parent directory exists
3. Confirm proper permissions on both paths
EOF
    exit $exit_code
else
    cat <<EOF

SUCCESS!
Rule output:
$irule_output

EOF
fi
