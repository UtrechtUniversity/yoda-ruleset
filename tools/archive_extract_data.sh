#!/bin/bash
###############################################################################
# iRODS Data Archive/Extract Script
#
# Supports two modes:
# 1. Archive: Creates an archive from an iRODS collection using msiArchiveCreate
# 2. Extract: Extracts an archive to an iRODS collection using msiArchiveExtract
###############################################################################

DEFAULT_RULE_ENGINE="irods_rule_engine_plugin-irods_rule_language-instance"
MODE=""
SOURCE_PATH=""
TARGET_PATH=""

# Helper function
usage() {
    cat <<EOF
iRODS Data Archive and Extract Utility

Archive Mode:
  Creates an archive from an iRODS collection using msiArchiveCreate

Extract Mode:
  Extracts an archive to an iRODS collection using msiArchiveExtract
  Files with the same name (already exist) will be skipped (not overwritten)

Usage: $0 -m MODE -s SOURCE_PATH -t TARGET_PATH

Required Arguments:
  -m, --mode               Operation mode: 'archive' or 'extract'
  -s, --source-path        Source path (collection for archive, archive file for extract)
  -t, --target-path        Target path (archive file for archive, collection for extract)

Examples:
  Archive a collection:
    $0 -m archive \\
       -s /tempZone/home/research-initial/data-package \\
       -t /tempZone/home/research-initial/archives/backup.tar

  Extract an archive:
    $0 -m extract \\
       -s /tempZone/home/research-initial/archives/backup.tar \\
       -t /tempZone/home/research-initial/extracted-data
EOF
}

# Validate arguments based on mode
validate_arguments() {
    local errors=0
    
    # Check mode
    if [[ "$MODE" != "archive" && "$MODE" != "extract" ]]; then
        echo "ERROR: Mode must be either 'archive' or 'extract'" >&2
        errors=$((errors+1))
    fi
    
    # Check required paths
    if [[ -z "$SOURCE_PATH" ]]; then
        echo "ERROR: Source path is required" >&2
        errors=$((errors+1))
    fi
    
    if [[ -z "$TARGET_PATH" ]]; then
        echo "ERROR: Target path is required" >&2
        errors=$((errors+1))
    fi
    
    # Mode-specific validations
    if [[ "$MODE" == "archive" ]]; then
        # In archive mode, source collection must not end with '/'
        if [[ "$SOURCE_PATH" != "/" && "$SOURCE_PATH" == */ ]]; then
            cat <<EOF >&2
ERROR: In archive mode, source path must not end with '/'
  Provided: $SOURCE_PATH

Please use source collection path without a trailing slash.
EOF
            errors=$((errors+1))
        fi

        # For archive mode, check that target is not inside source
        local normalized_source="${SOURCE_PATH%/}"
        local normalized_target="${TARGET_PATH%/*}"  # Get parent path
        
        if [[ "$normalized_target" == "$normalized_source"* ]]; then
            cat <<EOF >&2
ERROR: Archive target cannot be inside source collection!
  Source: $normalized_source
  Target: $TARGET_PATH

This would cause recursive archiving and is not permitted.
EOF
            errors=$((errors+1))
        fi
    elif [[ "$MODE" == "extract" ]]; then
        # Check for .zip extension (case-insensitive)
        if [[ "${SOURCE_PATH,,}" == *.zip ]]; then
            cat <<EOF >&2

ERROR: ZIP archive extraction is not supported for now.
Please download the archive and use a local application to extract such as unzip cmd (Linux/Mac), 7-Zip/WinZip (Windows)
EOF
            errors=$((errors+1))
        fi
    fi
    
    return $errors
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -s|--source-path)
            SOURCE_PATH="$2"
            shift 2
            ;;
        -t|--target-path)
            TARGET_PATH="$2"
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

# For archive mode: check if target archive already exists
if [[ "$MODE" == "archive" ]]; then
    if ils "$TARGET_PATH" &>/dev/null; then
        echo "WARNING: Archive target '$TARGET_PATH' already exists."
        read -p "Do you want to overwrite it? [y/N] " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted by user."
            exit 1
        else
            echo "Proceeding with overwrite..."
        fi
    fi
fi

# Execute the appropriate operation
echo "Starting $MODE operation:"
echo "  Source: $SOURCE_PATH"
echo "  Target: $TARGET_PATH"

# Create temp file for output capture
TEMP_OUTPUT=$(mktemp)

# Function to display elapsed time
elapsed_time() {
    local start=$1
    local mode=$2
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start))
        printf "\rElapsed time for %s operation: %02d:%02d:%02d (per 10s)" \
               "$mode" $((elapsed/3600)) $(((elapsed%3600)/60)) $((elapsed%60))
        sleep 10
    done
}

# Capture operation execution and time it
start_time=$(date +%s)

# Start elapsed time counter in background
elapsed_time "$start_time" "$MODE" &
timer_pid=$!

# Execute appropriate rule based on mode
if [[ "$MODE" == "archive" ]]; then
    # Archive creation
    irule -r "$DEFAULT_RULE_ENGINE" \
        "msiArchiveCreate(*archiveTargetPath, *sourceCollection, *targetResource, *status=0)" \
        "*archiveTargetPath=$TARGET_PATH%*sourceCollection=$SOURCE_PATH%*targetResource=null%*status=0" \
        "ruleExecOut" > "$TEMP_OUTPUT" 2>&1
    exit_code=$?
else
    # Archive extraction
    irule -r "$DEFAULT_RULE_ENGINE" \
        "msiArchiveExtract(*archivePath, *extractPath, *extractFile, *targetResource, *status=0)" \
        "*archivePath=$SOURCE_PATH%*extractPath=$TARGET_PATH%*extractFile=null%*targetResource=null%*status=0" \
        "ruleExecOut" > "$TEMP_OUTPUT" 2>&1
    exit_code=$?
fi

# Stop and clean up the timer
kill $timer_pid 2>/dev/null
printf "\n"  # Move to new line after timer output

# Read captured output
rule_output=$(cat "$TEMP_OUTPUT")
rm -f "$TEMP_OUTPUT"

# Check execution status
if [[ $exit_code -ne 0 ]]; then
    cat <<EOF

ERROR: $MODE operation failed
Exit code: $exit_code
Rule output:
$rule_output

Troubleshooting:
1. Verify source path exists: ils '$SOURCE_PATH'
2. Check target's parent directory exists
3. Confirm proper permissions on both paths
EOF
    exit $exit_code
else
    cat <<EOF

SUCCESS: $MODE operation completed!
Rule output:
$rule_output

EOF
fi
