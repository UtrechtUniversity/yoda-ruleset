#!/usr/bin/env python3
""" Update schema in iRODS from local filesystem.
"""

import argparse
import base64
import hashlib
import subprocess
import os
import re
import sys
from typing import List, Tuple, Union


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schemadirectory", help="Schema directory on local filesystem")
    parser.add_argument("schemacollection", help="Schema collection in iRODS")
    parser.add_argument("--default-resource", default="irodsResc",
                        help="Resource to put new data objects on")
    return parser.parse_args()


def main() -> None:
    args: argparse.Namespace = parse_args()
    anything_changed: bool = False
    anything_failed: bool = False
    for filename in ["metadata.json", "uischema.json"]:
        (sync_changed, sync_failed) = synchronize(args.schemadirectory, args.schemacollection, filename, args.default_resource)
        anything_failed = anything_failed or sync_failed
        anything_changed = anything_changed or sync_changed
    if anything_changed:
        print("Changed")
    sys.exit(1 if anything_failed else 0)


def data_object_exists(collection_name: str, dataobject_name: str) -> bool:
    checkexist_command = ["ils", os.path.join(collection_name, dataobject_name)]
    (checkexist_code, checkexist_stdout, checkexist_stderr) = run_command(checkexist_command)
    return "does not exist" not in checkexist_stderr


def get_checksum(path, checksumtype):
    if checksumtype == "md5":
        hsh = hashlib.md5()
    elif checksumtype == "sha2":
        hsh = hashlib.sha256()
    else:
        raise ValueError(f"Checksum type {checksumtype} not supported.")

    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if chunk:
                hsh.update(chunk)
            else:
                break

    while True:
        chunk = f.read(8192)
        if chunk:
            hsh.update(chunk)
        else:
            break

    if hsh.name == 'md5':
        return hsh.hexdigest()
    else:
        return base64.b64encode(hsh.digest()).decode('ascii')


def file_matches_checksum(path: str, checksum: str) -> bool:
    if checksum.startswith(("sha2:", "md5:")):
        checksum_type = checksum.split(":")[0]
        file_checksum = f"{checksum_type}:" + get_checksum(path, checksum_type)
        return file_checksum == checksum
    else:
        return False


def get_dataobject_checksum(collection_name: str, dataobject_name: str) -> Union[str, None]:
    if data_object_exists(collection_name, dataobject_name):
        get_checksum_command = ["ichksum", os.path.join(collection_name, dataobject_name)]
        (checksum_code, checksum_stdout, checksum_stderr) = run_command(get_checksum_command)
        if checksum_code != 0:
            return None
        else:
            checksum_stdout_fields = [e for e in re.split(r'\s+', checksum_stdout) if e != '']
            if (len(checksum_stdout_fields) > 0):
                return checksum_stdout_fields[-1]
            else:
                return None
    else:
        return None


def synchronize(schema_directory: str, schema_collection: str, filename: str, default_resource: str) -> Tuple[bool, bool]:
    local_path = os.path.join(schema_directory, filename)
    irods_path = os.path.join(schema_collection, filename)

    if data_object_exists(schema_collection, filename):
        # If data object already exists we just update all replicas. Using the default resource
        # would result in a hierarchy error if the data object is no longer on the default resource
        # due to resource tree changes.
        get_resc_command = ["iquest", "--no-page", "%s", f"SELECT DATA_RESC_HIER WHERE COLL_NAME = '{schema_collection}' and DATA_NAME = '{filename}'"]
        (resc_code, resc_stdout, resc_stderr) = run_command(get_resc_command)
        if resc_code == 0:
            resource_to_update = resc_stdout.split("\n")[0].rstrip().split(";")[0]
        else:
            print(f"Could not determine resource existing data object: {schema_collection}/{filename}")
            sys.exit(1)
    else:
        resource_to_update = default_resource

    # We determine if the data object has been changed by comparing checksums before and after the sync, since
    # we can't use a dry run or look at verbose output of irsync due to various known issues with irsync
    # See https://github.com/irods/irods/issues/8288 and https://github.com/irods/irods/issues/8277
    checksum_before_sync = get_dataobject_checksum(schema_collection, filename)
    if checksum_before_sync is not None and file_matches_checksum(local_path, checksum_before_sync):
        # No need to sync if local file contents match the data object in iRODS.
        return (False, False)

    # We may want to add the -a parameter instead if the data object already exists,
    # but we currently can't do this because of https://github.com/irods/irods/issues/8295
    sync_command = ["irsync", "-R", resource_to_update, local_path, "i:" + irods_path]
    (sync_code, sync_stdout, sync_stderr) = run_command(sync_command)
    sync_error = sync_code != 0
    checksum_after_sync = get_dataobject_checksum(schema_collection, filename)
    sync_updated = checksum_before_sync != checksum_after_sync
    return (sync_updated, sync_error)


def run_command(command: List[str]) -> Tuple[int, str, str]:
    process = subprocess.run(command, capture_output=True, text=True)
    return (process.returncode, process.stdout, process.stderr)


if __name__ == "__main__":
    main()
