# -*- coding: utf-8 -*-
"""Functions for handling schema updates within any yoda-metadata file."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'
# TODO: Update __init__ with the .py file name

__all__ = ['rule_batch_troubleshoot_published_data_packages']

import json
import os
import re
import time

import genquery
import session_vars

import meta
import meta_form
import schema
from schema_transformation import verify_package_schema
import schema_transformations
from util import *
from publication import get_collection_metadata, get_publication_config
import datacite


def find_full_package_path(data_packages, short_package_name):
    """
    Find the full path of a data package based on its short name.

    Parameters:
    - data_packages (list of str): List of full paths for data packages.
    - short_package_name (str): The short name of the data package to find.

    Returns:
    - str: The full path of the data package if found, otherwise None.
    """
    for path in data_packages:
        if short_package_name in path:
            return path
    print("Error: The data package '{}' does not exist in the provided list.".format(short_package_name))
    return None


@rule.make(inputs=[0], outputs=[1])  # FIXME: Take only 1 input temporarily
def rule_batch_troubleshoot_published_data_packages(ctx, requested_package):
    """
    Find published data packages based on a specific name or return all if 'all_published_packages' is provided.

    Arguments:
    - ctx: Context variable, usually containing session and environment data.
    - requested_package: The short name of the package to find or 'all_published_packages' to list all.
    """
    print("Requested package:", requested_package)

    # Retrieve all published data packages
    all_published_packages = find_published_data_packages(ctx)
    if not all_published_packages:
        print("No published packages found.")
        return

    # Determine which packages to process based on the input
    if requested_package == 'all_published_packages':
        data_packages = all_published_packages
    else:
        data_package_path = find_full_package_path(all_published_packages, requested_package)
        if data_package_path:
            data_packages = [data_package_path]
        else:
            print("Error: Requested package '{}' not found among published packages.".format(requested_package))
            return

    # Output the list of packages to be processed
    print("Data packages to be processed:", data_packages)

    for data_package in data_packages:
        print("checking", data_package)
        # Case 1 (maybe outside of the this rule)
        schema_check = verify_package_schema(ctx, data_package, {})['match_schema']
        #('check_schema results', {'match_schema': True, 'schema': 'core-0'})
        # Case 2
        missing_avus, unexpected_avus = check_data_package_system_avus(ctx, data_package)

        # Case 3
        versionDOI_check, baseDOI_check = check_datacite_doi_registration(ctx, data_package)
        print("versionDOI_check", versionDOI_check)
        print("baseDOI_check", baseDOI_check)

        # Case 4
        landingPage_check, combiJson_check = check_integrity_of_publication_files(ctx, data_package)

def find_published_data_packages(ctx):
    """
    Find all published data packages by matching AVUs including org_vault_status = "PUBLISHED".

    :param ctx: Context or session information for the database or API connection.
    :return: A list of collection names that have been published.
    """
    try:
        # Extract the user zone from context
        user_zone = user.zone(ctx)

        # Define the query condition to fetch data
        query_condition = (
            "COLL_NAME like '/{}/home/vault-%' AND "
            "META_COLL_ATTR_NAME = 'org_vault_status' AND "
            "META_COLL_ATTR_VALUE = 'PUBLISHED'".format(user_zone)
        )

        # Define attributes to fetch
        query_attributes = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS"
        print("Query condition:", query_condition)
        print("Finding all published data packages")

        # Execute the query
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)
        print("Query executed successfully")

        # Collect results
        data_packages = [row[0] for row in iter]  # Collecting only the collection names

        # Return the list of published data package names
        return data_packages

    except Exception as e:
        print("An error occurred while executing the query:", e)
        return []


# Case 2
def check_data_package_system_avus(ctx, data_package):
    """
    Checks whether a data package has the expected system AVUs that start with constants.UUORGMETADATAPREFIX (i.e, 'org_').
    This function compares the AVUs of the provided data package against a set of ground truth AVUs derived from
    a successfully published data package.

    :param ctx: Context object containing session and callback information.
    :param data_package: String representing the data package collection path.
    :return: A tuple containing sets of missing and unexpected AVUs.
    """

    print("Data package under check:", data_package)

    # Fetch AVUs of the data package and filter those starting with 'org_' directly into a set
    extracted_avus = {m.attr for m in avu.of_coll(ctx, data_package) if m.attr.startswith('org_')}
    print("Extracted AVUs:", extracted_avus)

    # Define the set of ground truth AVUs
    avu_names_suffix = [
        'publication_approval_actor', 'publication_randomId', 'license_uri',
        'publication_versionDOI', 'publication_dataCiteJsonPath', 'publication_license',
        'action_log', 'publication_anonymousAccess', 'publication_versionDOIMinted',
        'publication_accessRestriction', 'vault_status', 'publication_landingPagePath',
        'data_package_reference', 'publication_licenseUri', 'publication_publicationDate',
        'publication_vaultPackage', 'publication_submission_actor', 'publication_status',
        'publication_lastModifiedDateTime', 'publication_combiJsonPath',
        'publication_landingPageUploaded', 'publication_oaiUploaded',
        'publication_landingPageUrl', 'publication_dataCiteMetadataPosted'
    ]
    ground_truth_avus = {constants.UUORGMETADATAPREFIX + name for name in avu_names_suffix}

    # Find missing and unexpected AVUs
    missing_avus = ground_truth_avus - extracted_avus
    unexpected_avus = extracted_avus - ground_truth_avus

    print("Checking:", data_package)
    print("Missing AVUs:", missing_avus)
    print("Unexpected AVUs:", unexpected_avus)

    return (missing_avus, unexpected_avus)

# TODO: Create a ticket for the dois typo in metadata_get

# Case 3
def check_datacite_doi_registration(ctx, data_package):
    '''Check the versionDOI and baseDOI registration, ensuring we receive a 200 status code from the DataCite API.'''

    # Use the get_attribute_value function to simplify attribute retrieval
    try:
        versionDOI = get_attribute_value(ctx, data_package, "versionDOI")
        status_code = datacite.metadata_get(ctx, versionDOI)
        versionDOI_check = (status_code == 200)
        print("versionDOI:", versionDOI)
        print("DataCite response for versionDOI:", status_code)
    except ValueError as e:
        print("Error:", str(e))
        versionDOI_check = False

    try:
        baseDOI = get_attribute_value(ctx, data_package, "baseDOI")
        status_code = datacite.metadata_get(ctx, baseDOI)
        baseDOI_check = (status_code == 200)
        print("baseDOI:", baseDOI)
        print("DataCite response for baseDOI:", status_code)
    except ValueError as e:
        print("Error:", str(e))
        baseDOI_check = False

    # Return the results based on the DOI checks
    return (versionDOI_check, baseDOI_check)


import hashlib

def get_md5_of_file(file_path):
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:  # Open the file in binary mode
        for chunk in iter(lambda: f.read(4096), b""):  # Read the file in 4KB chunks
            hash_md5.update(chunk)  # Update the MD5 hash with the chunk
    return hash_md5.hexdigest()  # Return the hexadecimal MD5 hash

def calculate_md5(content):
    """Calculate and return the MD5 checksum for the provided content."""
    # Create an MD5 hash object
    hash_md5 = hashlib.md5()

    # Check if the content is a byte string
    if isinstance(content, bytes):
        # Update the hash object directly with the byte string
        hash_md5.update(content)
    else:
        # Encode and update the hash object with the string
        hash_md5.update(content.encode('utf-8'))

    # Return the hexadecimal MD5 hash
    return hash_md5.hexdigest()

# Example of reading the landing page content
# landingPage = data_object.read(ctx, landingPagePath)
# For demonstration, let's assume landingPage is a string variable already containing data
def calculate_md5_bytes(file_path):
    """Calculate and return the MD5 checksum for the provided file."""
    hash_md5 = hashlib.md5()  # Create a new MD5 hash object
    with open(file_path, 'rb') as f:  # Open the file in binary read mode
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)  # Update the hash with the bytes from the file
    return hash_md5.hexdigest()  # Return the hexadecimal MD5 checksum

import subprocess

def get_md5_remote_ssh(host, username, file_path):
    try:
        # Build the SSH command to execute md5sum remotely using .format()
        ssh_command = "ssh {username}@{host} md5sum -b {file_path}".format(
            username=username, host=host, file_path=file_path
        )

        # Run the command using Popen (for python2 version)
        process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = process.communicate()

        # Check if the command was executed successfully
        if process.returncode == 0:
            # Return only the MD5 hash part
            return stdout.strip().split()[0]
        else:
            print("Error:", stderr)
            return None
    except Exception as e:
        print("An error occurred: {e}".format(e=str(e)))
        return None

from util import data_object, msi
# TODO: Case4
# /var/www/moai/metadata/allinone/UU01/JCY2C2.json
# /var/www/landingpages/allinone/UU01/JCY2C2.html

def get_attribute_value(ctx, data_package, attribute_suffix):
    attr = constants.UUORGMETADATAPREFIX + "publication_" + attribute_suffix
    try:
        return next(m.value for m in avu.of_coll(ctx, data_package) if m.attr == attr)
    except StopIteration:
        raise ValueError("Attribute {} not found in AVU".format(attr))

def verify_file_integrity(ctx, data_package, attribute_suffix, remote_directory):
    print("attribute_suffix",attribute_suffix)
    file_path = get_attribute_value(ctx, data_package, attribute_suffix)
    print("file_path",file_path)
    local_data = data_object.read(ctx, file_path)
    local_md5 = calculate_md5(local_data)

    publication_config = get_publication_config(ctx)
    file_shortname = file_path.split("/")[-1].replace('-combi', '')
    print("file_shortname",file_shortname)
    remote_file_path = "/var/www/{}/{}/{}/{}".format(
        remote_directory, publication_config['yodaInstance'], publication_config['yodaPrefix'], file_shortname)
    remote_md5 = get_md5_remote_ssh("combined.yoda.test", "inbox", remote_file_path) # TODO: update

    print("Local MD5 ({}): {}".format(attribute_suffix, local_md5))
    print("Remote MD5 ({}): {}".format(attribute_suffix, remote_md5))

    return local_md5 == remote_md5

def check_integrity_of_publication_files(ctx, data_package):
    landing_page_verified = verify_file_integrity(ctx, data_package, "landingPagePath", "landingpages")
    combi_json_verified = verify_file_integrity(ctx, data_package, "combiJsonPath", "moai/metadata")

    return (landing_page_verified, combi_json_verified)
