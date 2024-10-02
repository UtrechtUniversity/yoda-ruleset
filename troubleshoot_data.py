# -*- coding: utf-8 -*-
"""Functions and rules for troubleshooting published data packages."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = [
    'api_batch_troubleshoot_published_data_packages',
    'rule_batch_troubleshoot_published_data_packages'
]

import json
from datetime import datetime

import genquery
import requests
import urllib3

import datacite
from meta import vault_metadata_matches_schema
from publication import get_publication_config
from util import *


def find_full_package_path(ctx, package_name, write_stdout):
    """
    Find the full path of a data package based on its short name.

    :param ctx:          Combined type of a callback and rei struct
    :param package_name: The short name of the data package to find.
    :param write_stdout: A boolean representing whether to write to stdout or rodsLog

    :returns: The full path of the data package if found, otherwise None.
    """
    try:
        query_condition = (
            "COLL_NAME like '%{}%'".format(package_name)
        )
        query_attributes = "COLL_NAME"
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)

        # Return full package path if exists
        for row in iter:
            return row[0]
    except Exception as e:
        log.write(ctx, "find_full_package_path: An error occurred while executing the query: {}".format(e), write_stdout)
        return None


def find_data_packages(ctx, write_stdout):
    """
    Find all data packages in Retry, Unrecoverable and Unknown status by matching its AVU.

    :param ctx:          Combined type of a callback and rei struct
    :param write_stdout: A boolean representing whether to write to stdout or rodsLog

    :returns:   A list of collection names that have not been processed successfully
    """
    user_zone = user.zone(ctx)

    try:
        # Get all the vault packages that have org_publication_status in metadata
        query_condition = (
            "COLL_NAME like '/{}/home/vault-%' AND "
            "META_COLL_ATTR_NAME = '{}publication_status'".format(user_zone, constants.UUORGMETADATAPREFIX)
        )
        query_attributes = "COLL_NAME"
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)

        # Collecting only the collection names
        return [row[0] for row in iter]

    except Exception as e:
        log.write(ctx, "find_data_packages: An error occurred while executing the query: {}".format(e), write_stdout)
        return []


def check_data_package_system_avus(ctx, data_package, write_stdout):
    """
    Checks whether a data package has the expected system AVUs that start with constants.UUORGMETADATAPREFIX (i.e, 'org_').
    This function compares the AVUs of the provided data package against a set of ground truth AVUs derived from
    a successfully published data package.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.
    :param write_stdout: A boolean representing whether to write to stdout or rodsLog

    :returns:            A tuple containing boolean results of checking results
    """

    # Fetch AVUs of the data package and filter those starting with 'org_'
    extracted_avus = {m.attr for m in avu.of_coll(ctx, data_package) if m.attr.startswith(constants.UUORGMETADATAPREFIX + 'publication_')}

    # Define the set of ground truth AVUs
    avu_names_suffix = [
        'publication_approval_actor', 'publication_randomId',
        'publication_versionDOI', 'publication_dataCiteJsonPath', 'publication_license',
        'publication_anonymousAccess', 'publication_versionDOIMinted',
        'publication_accessRestriction', 'publication_landingPagePath',
        'publication_licenseUri', 'publication_publicationDate',
        'publication_vaultPackage', 'publication_submission_actor', 'publication_status',
        'publication_lastModifiedDateTime', 'publication_combiJsonPath',
        'publication_landingPageUploaded', 'publication_oaiUploaded',
        'publication_landingPageUrl', 'publication_dataCiteMetadataPosted'
    ]

    # Define set of AVUs with more than one version of publication
    avu_names_base_suffix = [
        'publication_previous_version', 'publication_baseDOI', 'publication_baseRandomId',
        'publication_baseDOIMinted'
    ]

    if constants.UUORGMETADATAPREFIX + 'publication_previous_version' in extracted_avus:
        combined_avu_names_suffix = avu_names_base_suffix + avu_names_suffix
        ground_truth_avus = {constants.UUORGMETADATAPREFIX + name for name in combined_avu_names_suffix}
    else:
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

    if missing_avus:
        log.write(ctx, "check_data_package_system_avus: There are some missing AVUs in data package <{}> - {}".format(data_package, list(missing_avus)), write_stdout)

    if unexpected_avus:
        log.write(ctx, "check_data_package_system_avus: There are some unexpected AVUs in data package <{}> - {}".format(data_package, list(unexpected_avus)), write_stdout)

    return (results["no_missing_avus"], results["no_unexpected_avus"])


def check_datacite_doi_registration(ctx, data_package, offline, write_stdout):
    """
    Check the registration status of both versionDOI and baseDOI with the DataCite API,
    ensuring that both DOIs return a 200 status code, which indicates successful registration.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.
    :param offline:      Whether to not connect to datacite
    :param write_stdout: A boolean representing whether to write to stdout or rodsLog

    :returns:            A tuple of booleans indicating check success or not.
    """
    if offline:
        return True, True

    version_doi_check = False
    base_doi_check = False

    try:
        version_doi = get_attribute_value(ctx, data_package, "versionDOI")
        status_code = datacite.metadata_get(ctx, version_doi)
        version_doi_check = status_code == 200
    except ValueError as e:
        log.write(ctx, "check_datacite_doi_registration: Error while trying to get versionDOI - {}".format(e), write_stdout)

    previous_version = ''
    try:
        previous_version = get_attribute_value(ctx, data_package, "previous_version")
    except Exception:
        pass

    if previous_version:
        try:
            base_doi = get_attribute_value(ctx, data_package, "baseDOI")
            status_code = datacite.metadata_get(ctx, base_doi)
            base_doi_check = status_code == 200
        except ValueError as e:
            log.write(ctx, "check_datacite_doi_registration: Error while trying to get baseDOI - {}".format(e), write_stdout)

    return (version_doi_check, base_doi_check)


def get_attribute_value(ctx, data_package, attribute_suffix):
    """
    Retrieves the value given the suffix of the attribute from a data package.

    :param ctx:              Combined type of a callback and rei struct
    :param data_package:     String representing the data package collection path.
    :param attribute_suffix: Suffix of the attribute before adding prefix such as "org_publication_"

    :returns:                Value of the attribute.

    :raises ValueError:      If the attribute is not found in the data package's AVU.
    """

    # TODO extract to avu.py? need this?
    attr = constants.UUORGMETADATAPREFIX + "publication_" + attribute_suffix
    try:
        return next(m.value for m in avu.of_coll(ctx, data_package) if m.attr == attr)
    except Exception:
        raise ValueError("get_attribute_value: Attribute {} not found in AVU".format(attr))


def get_landingpage_paths(ctx, data_package, write_stdout):
    """Given a data package get what the path and remote url should be"""
    file_path = ''
    try:
        file_path = get_attribute_value(ctx, data_package, "landingPagePath")
        url = get_attribute_value(ctx, data_package, "landingPageUrl")
        return file_path, url

    except Exception:
        log.write(ctx, "get_landingpage_paths: Could not find landing page for data package: {}".format(data_package), write_stdout)
        return '', ''


def compare_local_remote_landingpage(ctx, file_path, url, offline, api_call):
    """
    Compares file contents between a file in irods and its remote version to verify their integrity.

    :param ctx:          Combined type of a callback and rei struct
    :param file_path:    Path to file in irods
    :param url:          URL of file on remote
    :param offline:      Whether to skip requests.get call
    :param api_call:     Boolean representing whether was called by api and not a script

    :returns:         True if the file contents match, False otherwise
    """
    write_stdout = not api_call
    # Local/irods file
    if api_call:
        # If called by technicaladmin, only check that the file exists since we don't have access to the contents
        return data_object.exists(ctx, file_path)
    else:
        try:
            local_data = data_object.read(ctx, file_path)
        except Exception:
            log.write(ctx, "compare_local_remote_landingpage: Local file not found at path {}.".format(file_path), write_stdout)
            return False

    if offline:
        return len(local_data) > 0

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.get(url, verify=False)
    except requests.exceptions.ConnectionError as e:
        log.write(ctx, "compare_local_remote_landingpage: Failed to connect to {}".format(url), write_stdout)
        log.write(ctx, "compare_local_remote_landingpage: Error: {}".format(e), write_stdout)
        return False

    if response.status_code != 200:
        log.write(ctx, "compare_local_remote_landingpage: Error {} when connecting to <{}>.".format(response.status_code, url), write_stdout)
        return False

    # Set encoding to utf-8 for the response text (otherwise will not match local_data)
    response.encoding = 'utf-8'

    if local_data == response.text:
        return True

    log.write(ctx, "compare_local_remote_landingpage: File contents at irods path <{}> and remote landing page <{}> do not match.".format(file_path, url), write_stdout)
    return False


def check_landingpage(ctx, data_package, offline, api_call):
    """
    Checks the integrity of landing page by comparing the contents

    :param ctx:                Combined type of a callback and rei struct
    :param data_package:       String representing the data package collection path.
    :param offline:            Whether to skip any checks that require external server access
    :param api_call:           Boolean of whether this is for an api call version of the troubleshooting script

    :returns:                  A tuple containing boolean results of checking
    """
    irods_file_path, landing_page_url = get_landingpage_paths(ctx, data_package, not api_call)
    if len(irods_file_path) == 0 or len(landing_page_url) == 0:
        return False

    return compare_local_remote_landingpage(ctx, irods_file_path, landing_page_url, offline, api_call)


def check_combi_json(ctx, data_package, publication_config, offline, write_stdout):
    """
    Checks the integrity of combi JSON by checking URL and existence of file.

    :param ctx:                Combined type of a callback and rei struct
    :param data_package:       String representing the data package collection path.
    :param publication_config: Dictionary of publication config
    :param offline:            Whether to skip any checks that require external server access
    :param write_stdout:       A boolean representing whether to write to stdout or rodsLog

    :returns:                  A tuple containing boolean results of checking
    """
    # Check that the combi json in irods exists
    file_path = ''
    try:
        file_path = get_attribute_value(ctx, data_package, "combiJsonPath")
    except Exception:
        pass
    exists = data_object.exists(ctx, file_path)
    if not exists:
        log.write(ctx, "check_combi_json: combi JSON file in irods does not exist: {}".format(file_path), write_stdout)
        return False

    if offline:
        return True

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Get the version doi
    version_doi = ''
    try:
        version_doi = get_attribute_value(ctx, data_package, "versionDOI")
    except Exception:
        pass
    url = "https://{}/oai/oai?verb=GetRecord&metadataPrefix=oai_datacite&identifier=oai:{}".format(publication_config["publicVHost"], version_doi)
    try:
        response = requests.get(url, verify=False)
    except requests.exceptions.ConnectionError as e:
        log.write(ctx, "check_combi_json: Failed to connect to {}".format(url), write_stdout)
        log.write(ctx, "check_combi_json: Error: {}".format(e), write_stdout)
        return False

    if response.status_code != 200:
        log.write(ctx, "check_combi_json: Error {} when connecting to <{}>.".format(response.status_code, url), write_stdout)
        return False

    # Look at the first few parts of the response for signs of error.
    if "idDoesNotExist" in response.text[:5000]:
        log.write(ctx, "check_combi_json: combiJson not found in oai for data package <{}>".format(data_package), write_stdout)
        return False

    return True


def print_troubleshoot_result(ctx, data_package, result):
    """Print the result of troubleshooting one package in human-friendly format"""
    pass_all_tests = all(result.values())

    log.write(ctx, "Results for: {}".format(data_package), True)
    if pass_all_tests:
        log.write(ctx, "Package passed all tests.", True)
    else:
        log.write(ctx, "Package FAILED one or more tests:", True)
        log.write(ctx, "Schema matches: {}".format(result['schema_check']), True)
        log.write(ctx, "All expected AVUs exist: {}".format(result['no_missing_AVUs_check']), True)
        log.write(ctx, "No unexpected AVUs: {}".format(result['no_unexpected_AVUs_check']), True)
        log.write(ctx, "Version DOI matches: {}".format(result['versionDOI_check']), True)
        log.write(ctx, "Base DOI matches: {}".format(result['baseDOI_check']), True)
        log.write(ctx, "Landing page matches: {}".format(result['landingPage_check']), True)
        log.write(ctx, "Combined JSON matches: {}".format(result['combiJson_check']), True)

    log.write(ctx, "", True)


def collect_troubleshoot_data_packages(ctx, requested_package, write_stdout):
    data_packages = []

    if requested_package == 'None':
        # Retrieve all data packages
        all_packages = find_data_packages(ctx, write_stdout)
        if not all_packages:
            log.write(ctx, "collect_troubleshoot_data_packages: No packages found.", write_stdout)
            return None

        data_packages = all_packages
    else:
        # Get full path of the given package
        full_package_path = find_full_package_path(ctx, requested_package, write_stdout)

        if not full_package_path:
            log.write(ctx, "collect_troubleshoot_data_packages: Data package '{}' cannot be found.".format(requested_package), write_stdout)
            return None

        data_packages.append(full_package_path)

    return data_packages


def batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline, api_call):
    """
    Troubleshoots published data packages.

    :param ctx:               Context that combines a callback and rei struct.
    :param requested_package: A string representing a specific data package path or all packages with failed publications.
    :param log_file:          A boolean representing to write results in log.
    :param offline:           A boolean representing whether to perform all checks without connecting to external servers.
    :param api_call:          Boolean of whether this is run by a script or api test.

    :returns: A dictionary of dictionaries providing the results of the job.
    """
    write_stdout = not api_call
    # Check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is not rodsadmin", write_stdout)
        return {}

    data_packages = collect_troubleshoot_data_packages(ctx, requested_package, write_stdout)
    if not data_packages:
        return {}
    schema_cache = {}
    results = {}

    # Troubleshooting
    for data_package in data_packages:
        log.write(ctx, "Troubleshooting data package: {}".format(data_package), write_stdout)
        result = {}
        if not api_call:
            schema_check_dict = vault_metadata_matches_schema(ctx, data_package, schema_cache, "troubleshoot-publications", write_stdout)
            result['schema_check'] = schema_check_dict['match_schema'] if schema_check_dict else False

        result['no_missing_AVUs_check'], result['no_unexpected_AVUs_check'] = check_data_package_system_avus(ctx, data_package, write_stdout)
        result['versionDOI_check'], result['baseDOI_check'] = check_datacite_doi_registration(ctx, data_package, offline, write_stdout)
        result['landingPage_check'] = check_landingpage(ctx, data_package, offline, write_stdout, api_call)
        publication_config = get_publication_config(ctx)
        result['combiJson_check'] = check_combi_json(ctx, data_package, publication_config, offline, write_stdout)

        results[data_package] = result

        if not api_call:
            print_troubleshoot_result(ctx, data_package, result)

        if log_file:
            log_loc = "/var/lib/irods/log/troubleshoot_publications.log"
            with open(log_loc, "a") as writer:
                writer.writelines("Batch run date and time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                writer.writelines('\n')
                writer.writelines("Troubleshooting data package: {}".format(data_package))
                writer.writelines('\n')
                json.dump(result, writer)
                writer.writelines('\n')

    return results


@api.make()
def api_batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline):
    """
    Wrapper for the batch script for troubleshooting published data packages.
    Runs a subset of the tests since "technicaladmin" is usually more restricted than "rods".

    :param ctx:               Combined type of a callback and rei struct
    :param requested_package: A string representing a specific data package path or all packages with failed publications.
    :param log_file:          A boolean representing to write results in log.
    :param offline:           A boolean representing whether to perform all checks without connecting to external servers.

    :returns: A dictionary of dictionaries providing the results of the job.
    """
    return batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline, True)


@rule.make(inputs=[0, 1, 2], outputs=[])
def rule_batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline):
    """
    Troubleshoots published data packages.

    Prints results of the following checks:
        1. Metadata schema compliance.
        2. Presence and correctness of expected AVUs.
        3. Registration with Data Cite.
        4. File integrity of landing page and combi JSON files.

    Operates on either a single specified package or all published packages, depending on the input.

    :param ctx:               Context that combines a callback and rei struct.
    :param requested_package: A string representing a specific data package path or all packages with failed publications.
    :param log_file:          A string boolean representing to write results in log.
    :param offline:           A string boolean representing whether to perform all checks without connecting to external servers.
    """
    offline = offline == "True"
    log_file = log_file == "True"

    batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline, False)
