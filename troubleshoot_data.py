# -*- coding: utf-8 -*-
"""Functions and rules for troubleshooting published data packages."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_troubleshoot_published_data_packages']

import hashlib
import json
import subprocess

import genquery

import datacite
from publication import get_publication_config
import session_vars
from schema_transformation import verify_package_schema
from util import *


def find_full_package_path(ctx, data_packages, short_package_name):
    """
    Find the full path of a data package based on its short name.

    :param ctx:                Combined type of a callback and rei struct
    :param data_packages:      List of full paths for data packages.
    :param short_package_name: The short name of the data package to find.

    :returns: The full path of the data package if found, otherwise None.
    """
    for path in data_packages:
        if short_package_name in path:
            return path
    log.write_stdout(ctx, "Error: The data package '{}' does not exist in the provided list.".format(short_package_name))
    return None


def published_data_package_exists(ctx, path):
    """Confirm whether path is to a published data package"""
    # TODO could this be a utility?

    # Define the query condition and attributes to fetch data
    query_condition = (
        "COLL_NAME = '{}' AND "
        "META_COLL_ATTR_NAME = 'org_vault_status' AND "
        "META_COLL_ATTR_VALUE = 'PUBLISHED'".format(path)
    )
    query_attributes = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS"
    iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)

    for _ in iter:
        return True

    return False


def find_published_data_packages(ctx):
    """
    Find all published data packages by matching its AVU that org_vault_status = "PUBLISHED".

    :param ctx: Combined type of a callback and rei struct

    :returns:   A list of collection names that have been published.
    """
    try:
        user_zone = user.zone(ctx)

        # Define the query condition and attributes to fetch data
        query_condition = (
            "COLL_NAME like '/{}/home/vault-%' AND "
            "META_COLL_ATTR_NAME = 'org_vault_status' AND "
            "META_COLL_ATTR_VALUE = 'PUBLISHED'".format(user_zone)
        )
        query_attributes = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS"
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)

        # Collecting only the collection names
        return [row[0] for row in iter]

    except Exception as e:
        log.write_stdout(ctx, "An error {} occurred while executing the query:".format(e))
        return []


def check_data_package_system_avus(ctx, data_package):
    """
    Checks whether a data package has the expected system AVUs that start with constants.UUORGMETADATAPREFIX (i.e, 'org_').
    This function compares the AVUs of the provided data package against a set of ground truth AVUs derived from
    a successfully published data package.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.

    :returns:            A tuple containing boolean results of checking results
    """

    # Fetch AVUs of the data package and filter those starting with 'org_'
    extracted_avus = {m.attr for m in avu.of_coll(ctx, data_package) if m.attr.startswith('org_')}

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

    results = {
        'no_missing_avus': not bool(missing_avus),
        'missing_avus': list(missing_avus),
        'no_unexpected_avus': not bool(unexpected_avus),
        'unexpected_avus': list(unexpected_avus)
    }

    return (results["no_missing_avus"], results["no_unexpected_avus"])


def check_datacite_doi_registration(ctx, data_package):
    """
    Check the registration status of both versionDOI and baseDOI with the DataCite API,
    ensuring that both DOIs return a 200 status code, which indicates successful registration.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.

    :returns:            A tuple of booleans indicating check success or not.
    """

    try:
        version_doi = get_attribute_value(ctx, data_package, "versionDOI")
        status_code = datacite.metadata_get(ctx, version_doi)
        version_doi_check = status_code == 200
    except ValueError as e:
        log.write_stdout(ctx, "Error: {} while trying to get versionDOI".format(e))
        version_doi_check = False

    try:
        base_doi = get_attribute_value(ctx, data_package, "baseDOI")
        status_code = datacite.metadata_get(ctx, base_doi)
        base_doi_check = status_code == 200
    except ValueError as e:
        log.write_stdout(ctx, "Error: {} while trying to get baseDOI".format(e))
        base_doi_check = False

    return (version_doi_check, base_doi_check)


def calculate_md5(content):
    """
    Computes the MD5 checksum of the provided content.

    :param content:  The content for which to compute the checksum.

    :returns:        The computed MD5 checksum as a hexadecimal string.
    """
    # Create an MD5 hash object
    hash_md5 = hashlib.md5()

    # Check if the content is a byte string
    if isinstance(content, bytes):
        hash_md5.update(content)
    else:
        hash_md5.update(content.encode('utf-8'))

    return hash_md5.hexdigest()


def get_md5_remote_ssh(ctx, host, username, file_path):
    """
    Calculate the MD5 checksum of a file on a remote server via SSH.

    :param ctx:       Combined type of a callback and rei struct
    :param host:      The hostname the remote server.
    :param username:  The username to log into the remote server.
    :param file_path: The path to the file on the remote server for which the MD5 checksum is calculated.

    :returns:         The MD5 checksum of the file if successful, None otherwise.
    """
    try:
        # Build the SSH command to execute md5sum remotely
        ssh_command = "ssh {username}@{host} md5sum -b {file_path}".format(
            username=username, host=host, file_path=file_path
        )

        # Run the command using Popen (for python2 version)
        # TODO: in copy_to_vault package, it may have subprocess method that we can copy here
        # TODO: convert to .run() in Python3
        process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        # returncode = subprocess.call(["irsync", "-rK", "i:{}/".format(coll), "i:{}/original".format(target)])
        stdout, stderr = process.communicate()

        # Return only the MD5 hash part
        if process.returncode == 0:
            return stdout.strip().split()[0]

        log.write(ctx, "Error: {}".format(stderr))
        return None
    except Exception as e:
        log.write(ctx, "An error occurred: {}".format(str(e)))
        return None


def get_attribute_value(ctx, data_package, attribute_suffix):
    """
    Retrieves the value given the suffix of the attribute from a data package.

    :param ctx:              Combined type of a callback and rei struct
    :param data_package:     String representing the data package collection path.
    :param attribute_suffix: Suffix of the attribute before adding prefix such as "org_publication_"

    :returns:                Value of the attribute.

    :raises ValueError:      If the attribute is not found in the data package's AVU.
    """

    attr = constants.UUORGMETADATAPREFIX + "publication_" + attribute_suffix
    try:
        return next(m.value for m in avu.of_coll(ctx, data_package) if m.attr == attr)
    except Exception:
        raise ValueError("Attribute {} not found in AVU".format(attr))


def verify_file_integrity(ctx, data_package, attribute_suffix, remote_host, remote_directory):
    """
    Compares MD5 checksums between a local file and its remote version to verify their integrity.

    :param ctx:              Combined type of a callback and rei struct
    :param data_package:     String representing the data package collection path.
    :param attribute_suffix: Suffix identifying the metadata attribute for the file path.
    :param remote_host:      Hostname for the remote host to look up in publication config
    :param remote_directory: Base directory on the remote server for the file.

    :returns:                True if the MD5 checksums match, False otherwise.

    :raises KeyError:        If host cannot be found in publication config
    """

    # Calculate md5 for the local file
    file_path = get_attribute_value(ctx, data_package, attribute_suffix)
    log.write_stdout(ctx, "file path: {}".format(file_path))
    # We are comparing small files so it should be ok to get the whole file
    local_data = data_object.read(ctx, file_path)
    local_md5 = calculate_md5(local_data)

    # Calculate md5 for the remote file
    publication_config = get_publication_config(ctx)
    if remote_host not in publication_config:
        raise KeyError("Host {} does not exist in publication config".format(remote_host))

    file_shortname = file_path.split("/")[-1].replace('-combi', '')
    log.write_stdout(ctx, "short: {}".format(file_shortname))
    remote_file_path = "/var/www/{}/{}/{}/{}".format(
        remote_directory, publication_config['yodaInstance'], publication_config['yodaPrefix'], file_shortname)
    log.write_stdout(ctx, "remote file path: {}".format(remote_file_path))

    remote_md5 = get_md5_remote_ssh(ctx, publication_config[remote_host], config.inbox_user, remote_file_path)

    if local_md5 == remote_md5:
        return True

    log.write_stdout(ctx, "MD5 of local and remote file don't match.")
    log.write_stdout(ctx, "Local MD5 ({}): {}".format(attribute_suffix, local_md5))
    log.write_stdout(ctx, "Remote MD5 ({}): {}".format(attribute_suffix, remote_md5))
    return False


def check_integrity_of_publication_files(ctx, data_package):
    """
    Checks the integrity of landingPage and CombiJson files by verifying their MD5 checksums in local against those in public server.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.

    :returns:            A tuple containing boolean results of checking
    """
    # publicVHost for landingpage, moaiHost for moai
    landing_page_verified = verify_file_integrity(ctx, data_package, "landingPagePath", "publicVHost", "landingpages")
    combi_json_verified = verify_file_integrity(ctx, data_package, "combiJsonPath", "moaiHost", "moai/metadata")
    return (landing_page_verified, combi_json_verified)


def print_troubleshoot_result(ctx, result):
    """Print the result of troubleshooting of one package in human-friendly format"""
    pass_all_tests = False
    for value in result.values():
        pass_all_tests = pass_all_tests and value

    log.write_stdout(ctx, "Results for: {}".format(result['data_package_path']))
    # TODO check these prompt messages
    if pass_all_tests:
        log.write_stdout(ctx, "Package passes all tests.")
    else:
        log.write_stdout(ctx, "Package FAILED one or more tests:")
        log.write_stdout(ctx, "Schema matches: {}".format(result['schema_check']))
        log.write_stdout(ctx, "All expected AVUs exist: {}".format(result['no_missing_avus_check']))
        log.write_stdout(ctx, "No unexpected AVUs: {}".format(result['no_unexpected_avus_check']))
        log.write_stdout(ctx, "Version DOI matches: {}".format(result['versionDOI_check']))
        log.write_stdout(ctx, "Base DOI matches: {}".format(result['baseDOI_check']))
        log.write_stdout(ctx, "Landing page matches: {}".format(result['landingPage_check']))
        log.write_stdout(ctx, "combiJson matches: {}".format(result['combiJson_check']))

    log.write_stdout(ctx, "")


@rule.make(inputs=[0, 1], outputs=[2])
def rule_batch_troubleshoot_published_data_packages(ctx, requested_package, log_loc):
    """
    Troubleshoots published data packages.

    :param ctx:               Context that combines a callback and rei struct.
    :param requested_package: A string representing a specific data package path or "all_published_data" for all packages.
    :param log_loc:           A string representing location to write a json log

    :returns: None.

    Prints results of the following checks:
        1. Metadata schema compliance.
        2. Presence and correctness of expected AVUs.
        3. Registration with Data Cite.
        4. File integrity of landing page and combi JSON files.

    Operates on either a single specified package or all published packages, depending on the input.
    """
    data_packages = []

    # Full path given
    if requested_package.startswith("/"):
        if not collection.exists(ctx, requested_package) or not published_data_package_exists(ctx, requested_package):
            log.write_stdout(ctx, "Error: Requested package '{}' not found among published packages.".format(requested_package))
            return

        data_packages.append(requested_package)
    else:
        # Retrieve all published data packages
        all_published_packages = find_published_data_packages(ctx)
        if not all_published_packages:
            log.write_stdout(ctx, "No published packages found.")
            return

        # Determine which packages to process based on the input
        if requested_package == 'all_published_packages':
            data_packages = all_published_packages
        else:
            data_package_path = find_full_package_path(ctx, all_published_packages, requested_package)
            if data_package_path:
                data_packages.append(data_package_path)
            else:
                log.write_stdout(ctx, "Error: Requested package '{}' not found among published packages.".format(requested_package))
                return

    # Troubleshooting
    for data_package in data_packages:
        log.write_stdout(ctx, "Troubleshooting: {}".format(data_package))
        schema_check = verify_package_schema(ctx, data_package, {})['match_schema']
        no_missing_avus_check, no_unexpected_avus_check = check_data_package_system_avus(ctx, data_package)
        version_doi_check, base_doi_check = check_datacite_doi_registration(ctx, data_package)
        landing_page_check, combi_json_check = check_integrity_of_publication_files(ctx, data_package)

        # Collect results for current data package
        result = {
            'data_package_path': data_package,
            'schema_check': schema_check,
            'no_missing_avus_check': no_missing_avus_check,
            'no_unexpected_avus_check': no_unexpected_avus_check,
            'versionDOI_check': version_doi_check,
            'baseDOI_check': base_doi_check,
            'landingPage_check': landing_page_check,
            'combiJson_check': combi_json_check
        }

        print_troubleshoot_result(ctx, result)
        # TODO proper check?
        if len(log_loc):
            with open(log_loc, "a") as writer:
                json.dump(result, writer)
                writer.writelines('\n')
