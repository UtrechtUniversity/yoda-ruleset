#!/usr/bin/env python3

"""
   edit-vault-metadata : script for manually editing metadata of a data package
   in the vault.

   By default, the script lets the vault ingest workflow handle ingestion of new metadata
   into the vault. In case where that is not possible (e.g. because the vault group no longer
   has a research group, because the category does not have a datamanager group, etc.), you
   can use the --direct option to make the script update the vault metadata directly, bypassing
   the normal vault ingest workflow.

   In direct mode, this script takes care of:
   - Finding the current (latest) metadata file of the data package
   - Downloading it
   - Starting an editor to edit it
   - Re-uploading the metadata file as a new version
   - Setting the right ACLs
   - Updating the provenance log of the data package
"""

import argparse
import filecmp
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import List, Tuple, Union


def get_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        'collection',
        help='Vault collection')

    parser.add_argument(
        '-m', '--log-message',
        default="metadata manually updated by technical admin",
        required=False,
        help="Message to be logged in the provenance log for this edit (only applies in direct mode)")
    parser.add_argument(
        '-d', '--direct',
        action='store_true',
        default=False,
        help="Edit file directly in vault collection. This side-steps the normal ingestion process, but can be needed for vault groups without a research group, categories without a datamanager group, and other situations not support by the default ingestion process.")

    parsed_args = parser.parse_args()

    if not parsed_args.collection.startswith("/"):
        sys.exit("Error: collection must be an absolute path.")

    return parsed_args


def start_editor(filename: str):
    editor = os.environ.get('EDITOR', 'vim')
    subprocess.call([editor, filename])


def check_edited_file_changed(filename: str) -> bool:
    return not filecmp.cmp(filename, filename + ".orig")


def get_latest_metadata_file(collection: str) -> Union[str, None]:
    latest_timestamp = None
    latest_filename = None
    lines = subprocess.check_output(["ils", collection])
    for line in lines.decode("utf-8").split("\n"):
        match = re.search(r"^  (yoda-metadata\[(\d+)\]\.json)\s*$", line)
        if match and (latest_timestamp is None or match.group(2)
                      > latest_timestamp):
            latest_filename = match.group(1)
            latest_timestamp = match.group(2)
    return latest_filename


def apply_acls(path: str, acls: List[Tuple[str, str]]):
    for acl in acls:
        retcode = subprocess.call(["ichmod", "-M", acl[1], acl[0], path])
        if retcode != 0:
            sys.exit("Could not set ACL {}:{} for {}".format(acl[1], acl[0], path))


def create_collection(path: str):
    retcode = subprocess.call(["imkdir", path])
    if retcode != 0:
        sys.exit("Error: could not create collection " + path)


def create_collection_and_apply_acls_recursively(path: str, acls: List[Tuple[str, str]]):
    path_components = path.split("/")
    for (level, _) in enumerate(path_components):
        current_collection = "/".join(path_components[:level + 1])
        current_collection_exists = collection_exists(current_collection)
        if level >= 2 and current_collection_exists:
            apply_acls(current_collection, acls)
        elif level >= 3 and not current_collection_exists:
            create_collection(current_collection)
            apply_acls(current_collection, acls)


def get_dataobject_acls(path: str) -> List[Tuple[str, str]]:
    results = []
    lines = subprocess.check_output(["ils", "-A", path])
    for line in lines.decode("utf-8").split("\n"):
        match = re.search(r"^        ACL - ([\S\s]+)$", line)
        if match:
            acl_line = match.group(1)
            for acl_entry in acl_line.replace("read object", "read").replace("g:", "").split():
                (acl_group, acl_priv) = acl_entry.split(":")
                acl_clean_group = acl_group.split("#")[0]
                results.append((acl_clean_group, acl_priv))
    return results


def upload_new_metadata_file(local_filename: str, remote_filename: str):
    print("Uploading {} to {}".format(local_filename, remote_filename))
    retcode = subprocess.call(["iput", local_filename, remote_filename])
    if retcode != 0:
        sys.exit("Error: could not upload metadata file {} to {}.".format(
                 local_filename,
                 remote_filename))


def download_metadata_file(destination_dir: str, remote_path: str) -> str:
    local_path_edit = os.path.join(destination_dir,
                                   os.path.basename(remote_path))
    retcode = subprocess.call(["iget", remote_path, local_path_edit])
    if retcode != 0:
        sys.exit("Error: could not download metadata file {} to {}.".format(
                 remote_path,
                 local_path_edit))

    local_path_orig = os.path.join(destination_dir,
                                   os.path.basename(remote_path)) + ".orig"
    retcode = subprocess.call(["iget", remote_path, local_path_orig])
    if retcode != 0:
        sys.exit("Error: could not download metadata file {} to {}.".format(
                 remote_path,
                 local_path_orig))

    return local_path_edit


def get_datamanager_vault_subcollection(datamanager_collection: str, vault_path: str):
    vault_group = vault_path.split("/")[3]
    return os.path.join(os.path.join(datamanager_collection, vault_group), os.path.basename(vault_path))


def get_new_metadata_name(collection: str, zone_name: str, direct_mode: bool) -> str:
    if direct_mode:
        return os.path.join(collection, "yoda-metadata[{}].json".format(str(int(time.time()))))

    research_collection = get_research_collection_for_vault_path(collection)
    if research_collection is None:
        sys.exit("Error: cannot use default workflow. This vault group does not have a research group anymore. You can bypass the default workflow using --direct mode.")
    research_group = get_research_group_for_research_collection(research_collection)
    category = get_category_research_group(research_group)
    dm_collection = get_datamanager_collection_for_category(category, zone_name)
    if dm_collection is None:
        sys.exit("Error: cannot use default workflow. The research group for this vault group does not have a datamanager group. You can bypass the default workflow using --direct mode.")
    dm_subcollection = get_datamanager_vault_subcollection(dm_collection, collection)
    return os.path.join(dm_subcollection, "yoda-metadata.json")


def update_provenance_log(vault_collection: str, log_message: str):
    retcode = subprocess.call(["/etc/irods/yoda-ruleset/tools/log-provenance-action.sh", vault_collection, "rods", log_message])
    if retcode != 0:
        sys.exit("Error: could not update provenance log for {}.".format(vault_collection))


def collection_exists(path: str) -> bool:
    result = subprocess.run(["iquest", "%s", "--no-page", "SELECT COLL_NAME WHERE COLL_NAME ='{}'".format(path)], capture_output=True, text=True)
    if result.returncode == 0 and path in result.stdout:
        return True
    elif result.returncode == 1 and "CAT_NO_ROWS_FOUND" in result.stdout:
        return False
    else:
        sys.exit("Unexpected result when checking for existence of collection " + path)


def get_research_collection_for_vault_path(path: str) -> str:
    if not path.startswith("/"):
        sys.exit("Error: need absolute vault path to determine research group.")
    vault_main_collection = "/".join(path.split("/")[:4])
    research_collection = vault_main_collection.replace("vault-", "research-", 1)
    return research_collection


def get_research_group_for_research_collection(path: str) -> str:
    if not path.startswith("/"):
        sys.exit("Error: need absolute research collectoin path to determine research group.")
    return path.split("/")[3]


def get_zone_name_from_path(path: str) -> str:
    if not path.startswith("/"):
        sys.exit("Error: need absolute research collection path to determine research group.")
    return path.split("/")[1]


def get_research_group_for_vault_path(path: str) -> Union[str, None]:
    research_collection = get_research_collection_for_vault_path(path)
    if collection_exists(research_collection):
        return get_research_group_for_research_collection(path)
    else:
        return None


def get_datamanager_collection_for_category(category: str, zone_name: str) -> Union[str, None]:
    datamanager_collection = "/{}/home/datamanager-{}".format(zone_name, category)
    return datamanager_collection if collection_exists(datamanager_collection) else None


def get_category_research_group(research_group: str) -> str:
    result = subprocess.run(["iquest", "%s", "--no-page", "SELECT META_USER_ATTR_VALUE WHERE USER_NAME = '{}' and META_USER_ATTR_NAME = 'category'".format(research_group)], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.split("\n")[0]
    else:
        sys.exit("Error: could not find category for research group " + research_group)


def main():
    args = get_args()
    if not collection_exists(args.collection):
        sys.exit("Error: collection {} does not exist.".format(args.collection))
    zone_name = get_zone_name_from_path(args.collection)
    with tempfile.TemporaryDirectory() as tempdir:
        metadata_file = get_latest_metadata_file(args.collection)
        metadata_file_path = os.path.join(args.collection, metadata_file)
        metadata_acls = get_dataobject_acls(metadata_file_path)
        print("Metadata data object: " + metadata_file_path)
        local_filename = download_metadata_file(tempdir, metadata_file_path)
        start_editor(local_filename)
        if check_edited_file_changed(local_filename):
            remote_filename = get_new_metadata_name(args.collection, zone_name, args.direct)
            if not args.direct:
                dm_subcollection = os.path.dirname(remote_filename)
                print("Creating datamanager subcollection for vault group " + dm_subcollection + " recursively.")
                create_collection_and_apply_acls_recursively(dm_subcollection, [("rods", "own")])
            print("Uploading new version of metadata.")
            upload_new_metadata_file(local_filename, remote_filename)
            if args.direct:
                print("Applying ACLs to new metadata.")
                apply_acls(remote_filename, metadata_acls)
                print("Updating provenance log ...")
                update_provenance_log(args.collection, args.log_message)
                print("Done.")
        else:
            print("Not updating metadata, since it wasn't changed.")


if __name__ == "__main__":
    main()
