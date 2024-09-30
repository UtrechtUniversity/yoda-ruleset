# -*- coding: utf-8 -*-
"""Functions and rules for troubleshooting published data packages."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_troubleshoot_published_data_packages']

import json
from datetime import datetime

import genquery
import requests

import datacite
from meta import vault_metadata_matches_schema
from publication import get_publication_config
from util import *


def find_full_package_path(ctx, package_name):
    """
    Find the full path of a data package based on its short name.

    :param ctx:                Combined type of a callback and rei struct
    :param package_name:       The short name of the data package to find.

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
        log.write_stdout(ctx, "find_full_package_path: An error occurred while executing the query: {}".format(e))
        return None


def find_data_packages(ctx):
    """
    Find all data packages in Retry, Unrecoverable and Unknown status by matching its AVU.

    :param ctx: Combined type of a callback and rei struct

    :returns:   A list of collection names that have not been processed successfully
    """
    user_zone = user.zone(ctx)

    try:
        # Get all the vault packages that have org_publication_status in metadata
        query_condition = (
            "COLL_NAME like '/{}/home/vault-%' AND "
            "META_COLL_ATTR_NAME = '{}publication_status'".format(user_zone, constants.UUORGMETADATAPREFIX)
        )
        # TODO make this select shorter?
        query_attributes = "COLL_NAME"
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)

        # Collecting only the collection names
        return [row[0] for row in iter]

    except Exception as e:
        log.write_stdout(ctx, "find_data_packages: An error occurred while executing the query: {}".format(e))
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
        log.write_stdout(ctx, "check_data_package_system_avus: There are some missing AVUs in data package <{}> - {}"
                         .format(data_package, list(missing_avus)))

    if unexpected_avus:
        log.write_stdout(ctx, "check_data_package_system_avus: There are some unexpected AVUs in data package <{}> - {}"
                         .format(data_package, list(unexpected_avus)))

    return (results["no_missing_avus"], results["no_unexpected_avus"])


def check_datacite_doi_registration(ctx, data_package):
    """
    Check the registration status of both versionDOI and baseDOI with the DataCite API,
    ensuring that both DOIs return a 200 status code, which indicates successful registration.

    :param ctx:          Combined type of a callback and rei struct
    :param data_package: String representing the data package collection path.

    :returns:            A tuple of booleans indicating check success or not.
    """
    version_doi_check = False
    base_doi_check = False

    try:
        version_doi = get_attribute_value(ctx, data_package, "versionDOI")
        status_code = datacite.metadata_get(ctx, version_doi)
        version_doi_check = status_code == 200
    except ValueError as e:
        log.write_stdout(ctx, "check_datacite_doi_registration: Error while trying to get versionDOI - {}".format(e))

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
            log.write_stdout(ctx, "check_datacite_doi_registration: Error while trying to get baseDOI - {}".format(e))

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


def get_landingpage_paths(ctx, data_package, publication_config):
    """Given a data package, and publication config, get what the remote url should be"""
    if not publication_config["publicVHost"]:
        raise KeyError("get_landingpage_paths: Host does not exist in publication config.")

    file_path = ''
    file_shortname = ''
    try:
        file_path = get_attribute_value(ctx, data_package, "landingPagePath")
        file_shortname = file_path.split("/")[-1]

        # Example url: https://public.yoda.test/allinone/UU01/PPQEBC.html
        url = "https://{}/{}/{}/{}".format(
            publication_config["publicVHost"], publication_config['yodaInstance'], publication_config['yodaPrefix'], file_shortname)
        return file_path, url

    except Exception:
        log.write_stdout(ctx, "get_landingpage_paths: Could not find landing page for data package: {}".format(data_package))
        return '', ''


def compare_local_remote_landingpage(ctx, file_path, url, offline):
    """
    Compares file contents between a file in irods and its remote version to verify their integrity.

    :param ctx:       Combined type of a callback and rei struct
    :param file_path: Path to file in irods
    :param url:       URL of file on remote
    :param offline:   Whether to skip requests.get call

    :returns:         True if the file contents match, False otherwise
    """
    # Get local file
    # We are comparing small files so it should be ok to get the whole file
    try:
        local_data = data_object.read(ctx, file_path)
    except Exception:
        log.write_stdout(ctx, "compare_local_remote_landingpage: Local file not found at path {}.".format(file_path))
        return False

    if offline:
        return len(local_data) > 0

    try:
        response = requests.get(url, verify=False)
    except requests.exceptions.ConnectionError as e:
        log.write_stdout(ctx, "compare_local_remote_landingpage: Failed to connect to {}".format(url))
        log.write_stdout(ctx, "compare_local_remote_landingpage: Error: {}".format(e))
        return False

    if response.status_code != 200:
        log.write_stdout(ctx, "compare_local_remote_landingpage: Error {} when connecting to <{}>.".format(response.status_code, url))
        return False

    if local_data == response.text:
        return True

    log.write_stdout(ctx, "compare_local_remote_landingpage: File contents at irods path <{}> and remote landing page <{}> do not match.".format(file_path, url))
    return False


def check_landingpage(ctx, data_package, publication_config, offline):
    """
    Checks the integrity of landing page by comparing the contents

    :param ctx:                Combined type of a callback and rei struct
    :param data_package:       String representing the data package collection path.
    :param publication_config: Dictionary of publication config
    :param offline:            Whether to skip any checks that require external server access

    :returns:                  A tuple containing boolean results of checking
    """
    irods_file_path, landing_page_url = get_landingpage_paths(ctx, data_package, publication_config)
    if len(irods_file_path) == 0 or len(landing_page_url) == 0:
        return False

    return compare_local_remote_landingpage(ctx, irods_file_path, landing_page_url, offline)


def check_combi_json(ctx, data_package, publication_config, offline):
    """
    Checks the integrity of combi JSON by checking URL and existence of file.

    :param ctx:                Combined type of a callback and rei struct
    :param data_package:       String representing the data package collection path.
    :param publication_config: Dictionary of publication config
    :param offline:            Whether to skip any checks that require external server access

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
        log.write_stdout(ctx, "check_combi_json: combi JSON file in irods does not exist: {}".format(file_path))
        return False

    if offline:
        return True

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
        log.write_stdout(ctx, "check_combi_json: Failed to connect to {}".format(url))
        log.write_stdout(ctx, "check_combi_json: Error: {}".format(e))
        return False

    if response.status_code != 200:
        log.write_stdout(ctx, "check_combi_json: Error {} when connecting to <{}>.".format(response.status_code, url))
        return False

    # Look at the first few parts of the response for signs of error.
    if "idDoesNotExist" in response.text[:5000]:
        log.write_stdout(ctx, "check_combi_json: combiJson not found in oai for data package <{}>".format(data_package))
        return False

    return True


def print_troubleshoot_result(ctx, result):
    """Print the result of troubleshooting of one package in human-friendly format"""
    pass_all_tests = False
    for value in result.values():
        pass_all_tests = pass_all_tests and value

    log.write_stdout(ctx, "Results for: {}".format(result['data_package_path']))
    # TODO check these prompt messages
    if pass_all_tests:
        log.write_stdout(ctx, "Package passed all tests.")
    else:
        log.write_stdout(ctx, "Package FAILED one or more tests:")
        log.write_stdout(ctx, "Schema matches: {}".format(result['schema_check']))
        log.write_stdout(ctx, "All expected AVUs exist: {}".format(result['no_missing_avus_check']))
        log.write_stdout(ctx, "No unexpected AVUs: {}".format(result['no_unexpected_avus_check']))
        log.write_stdout(ctx, "Version DOI matches: {}".format(result['versionDOI_check']))
        log.write_stdout(ctx, "Base DOI matches: {}".format(result['baseDOI_check']))
        log.write_stdout(ctx, "Landing page matches: {}".format(result['landingPage_check']))
        log.write_stdout(ctx, "Combined JSON matches: {}".format(result['combiJson_check']))

    log.write_stdout(ctx, "")


def collect_troubleshoot_data_packages(ctx, requested_package):
    data_packages = []

    if requested_package == 'None':
        # Retrieve all data packages
        all_packages = find_data_packages(ctx)
        if not all_packages:
            log.write_stdout(ctx, "collect_troubleshoot_data_packages: No packages found.")
            return None

        data_packages = all_packages
    else:
        # Get full path of the given package
        full_package_path = find_full_package_path(ctx, requested_package)

        if not full_package_path:
            log.write_stdout(ctx, "collect_troubleshoot_data_packages: Data package '{}' cannot be found.".format(requested_package))
            return None

        data_packages.append(full_package_path)

    return data_packages


@rule.make(inputs=[0, 1, 2], outputs=[])
def rule_batch_troubleshoot_published_data_packages(ctx, requested_package, log_file, offline):
    """
    Troubleshoots published data packages.

    :param ctx:               Context that combines a callback and rei struct.
    :param requested_package: A string representing a specific data package path or all packages with failed publications.
    :param log_file:          A string representing to write json results in log.
    :param offline:           A string representing whether to perform all checks without connecting to external servers.

    :returns: None.

    Prints results of the following checks:
        1. Metadata schema compliance.
        2. Presence and correctness of expected AVUs.
        3. Registration with Data Cite.
        4. File integrity of landing page and combi JSON files.

    Operates on either a single specified package or all published packages, depending on the input.
    """
    offline = offline == "True"
    write_log_file = log_file == "True"

    # Check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write_stdout(ctx, "User is no rodsadmin")
        return

    data_packages = collect_troubleshoot_data_packages(ctx, requested_package)
    if not data_packages:
        return
    schema_cache = {}

    # Troubleshooting
    for data_package in data_packages:
        log.write_stdout(ctx, "Troubleshooting data package: {}".format(data_package))
        schema_check = vault_metadata_matches_schema(ctx, data_package, schema_cache, "troubleshoot-publications")['match_schema']
        no_missing_avus_check, no_unexpected_avus_check = check_data_package_system_avus(ctx, data_package)
        version_doi_check, base_doi_check = check_datacite_doi_registration(ctx, data_package)
        publication_config = get_publication_config(ctx)
        landing_page_check = check_landingpage(ctx, data_package, publication_config, offline)
        combi_json_check = check_combi_json(ctx, data_package, publication_config, offline)

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
        # If user is admin -> create log if log_file is true
        if write_log_file:
            log_loc = "/var/lib/irods/log/troubleshoot_publications.log"
            with open(log_loc, "a") as writer:
                writer.writelines("Batch run date and time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                writer.writelines('\n')
                writer.writelines("Troubleshooting data package: {}".format(data_package))
                writer.writelines('\n')
                json.dump(result, writer)
                writer.writelines('\n')
