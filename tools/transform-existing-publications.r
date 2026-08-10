#!/usr/bin/irule -r irods_rule_engine_plugin-python-instance -F
#
# Transform existing publications according to the new changes in the publication process.
#
# Parameters:
# modify_prefix:        If True, this script will convert all the prefixes from yoda to version
#                       and add prefix version to DOIAvailable and DOI Minted variables.
# modify_basedoiminted: If True, this script will copy baseDOIMinted attribute value from new version
#                       to previous version of data package.
# package:              If a data package is specified, this script will perform the above operations
#                       only on data packages related to it. If none is specified, operations will
#                       be performed on all data packages in the zone where the script is executed from.
#
# irule -r irods_rule_engine_plugin-python-instance -F /etc/irods/yoda-ruleset/tools/transform-existing-publications.r '*modify_prefix=False' '*modify_basedoiminted=True' '*package=/path/to/collection'
#
import subprocess

import genquery
import session_vars
from tstrings import t

import constants


def prefix_transformation(zone, coll_name, callback):
    """Replace 'yoda' prefix with 'version'. Add 'version' prefix to
    DOIAvailable and DOIMinted AVUs.

    :param zone:        iRODS zone
    :param coll_name:   iRODS collection name (optional)
    :param callback:    iRODS callback
    """
    # Check if specified package (or any package in current zone, if none is specified) still has 'yoda' prefixes or DOIAvailable / DOIMinted AVUs
    if coll_name == '':
        change_prefix = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            f"COLL_ZONE_NAME = '{zone}' AND META_COLL_ATTR_NAME LIKE '{constants.UUORGMETADATAPREFIX}publication_yoda%'",
            genquery.AS_TUPLE,
            callback)

        add_prefix = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            f"COLL_ZONE_NAME = '{zone}' AND META_COLL_ATTR_NAME in ('{constants.UUORGMETADATAPREFIX}publication_DOIAvailable', '{constants.UUORGMETADATAPREFIX}publication_DOIMinted')",
            genquery.AS_TUPLE,
            callback)
    else:
        change_prefix = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            t("COLL_NAME = '{coll_name}' AND META_COLL_ATTR_NAME LIKE '{constants.UUORGMETADATAPREFIX}publication_yoda%'"),
            genquery.AS_TUPLE,
            callback)

        add_prefix = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
            t("COLL_NAME = '{coll_name}' AND META_COLL_ATTR_NAME in ('{constants.UUORGMETADATAPREFIX}publication_DOIAvailable', '{constants.UUORGMETADATAPREFIX}publication_DOIMinted')"),
            genquery.AS_TUPLE,
            callback)

    # Replace 'yoda' prefix with 'version'
    for row in change_prefix:
        callback.writeLine("stdout", f"Changing 'yoda' prefix to 'version' for collection: {row[0]}")
        subprocess.call(["imeta", "mod", "-C", row[0], row[1], row[2], f"n:{row[1].replace('yoda', 'version')}", "v:{row[2]}"])

    # Add 'version' prefix to DOIAvailable and DOIMinted AVUs
    for row in add_prefix:
        callback.writeLine("stdout", f"Adding 'version' prefix to DOIAvailable and DOIMinted AVUs for collection: {row[0]}")
        attr_name = row[1].rsplit('_', 1)[0] + "_version" + row[1].split('_')[-1]
        subprocess.call(["imeta", "mod", "-C", row[0], row[1], row[2], f"n:{attr_name}", f"v:{row[2]}"])


def datapackages_and_versions(zone, coll_name, callback):
    """Get published data packages and their newer version stored in metadata.

    :param zone:        iRODS zone
    :param coll_name:   iRODS collection name (optional)
    :param callback:    iRODS callback

    :returns: List of relevant data packages
    """
    package_list = []

    # If a collection is specified, query its newer version (if exists); if not, query all data packages with newer versions in current zone
    if coll_name == '':
        datapackages = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_VALUE",
            f"COLL_ZONE_NAME = '{zone}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}publication_next_version'",
            genquery.AS_LIST,
            callback)
    else:
        datapackages = genquery.row_iterator(
            "COLL_NAME, META_COLL_ATTR_VALUE",
            t("COLL_NAME = '{coll_name}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}publication_next_version'"),
            genquery.AS_LIST,
            callback)

    # Create list with placeholders for baseDOIMinted values
    for row in datapackages:
        package_list.append([row[0], "", row[1], ""])

    return package_list


def basedoiminted_value(zone, package, callback):
    """ Get baseDOIMinted value from the metadata of a data package.

    :param zone:     iRODS zone
    :param package:  Data package to get baseDOIMinted from
    :param callback: iRODS callback

    :returns: Value of baseDOIMinted attribute in the metadata
    """
    value = ""

    basedoiminted = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        t("COLL_ZONE_NAME = '{zone}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}publication_baseDOIMinted' AND COLL_NAME = '{package}'"),
        genquery.AS_LIST,
        callback)

    for row in basedoiminted:
        value = row[1]

    return value


def basedoiminted_correction(zone, list, callback):
    """ Get the baseDOIMinted attribute and value from previous and new version
    of data package. If the previous version does not have baseDOIMinted, get the
    value from new version and add it to metadata.

    :param zone:     iRODS zone
    :param list:     List of published data packages with their newer versions
    :param callback: iRODS callback

    :returns: List of data packages that do not have baseDOIMinted value
    """

    transformed_data_packages = []

    for row in list:
        # Get baseDOIMinted value from previous version
        row[1] = basedoiminted_value(zone, row[0], callback)

        # Get baseDOIMinted value from new version
        row[3] = basedoiminted_value(zone, row[2], callback)

        if row[1] == '':
            callback.writeLine("stdout", f"Modify baseDOIMinted attribute for collection: {row[0]}")
            try:
                subprocess.call(["imeta", "add", "-C", row[0], f"{constants.UUORGMETADATAPREFIX}publication_baseDOIMinted", row[3]])
                transformed_data_packages.append(row[0])
            except Exception as e:
                callback.writeLine("stdout", f"modify_basedoiminted: Error while adding baseDOIMinted to metadata for collection: {row[0]} - {e}")


def main(rule_args, callback, rei):
    modify_prefix = global_vars["*modify_prefix"]
    modify_basedoiminted = global_vars["*modify_basedoiminted"]
    package = global_vars["*package"]

    zone = session_vars.get_map(rei)['client_user']['irods_zone']

    # Verify existence of a data package if one is specified
    if package != '' and len(list(genquery.Query(callback, "COLL_ID", t("COLL_NAME = '{package}'")))) <= 0:
        callback.writeLine("stdout", "Specified collection was not found.")
    else:
        if modify_prefix == 'True':
            try:
                prefix_transformation(zone, package, callback)
            except Exception as e:
                callback.writeLine("stdout", f"prefix_transformation: Error encountered while modifying prefix for existing publications - {e}")

        if modify_basedoiminted == 'True':
            datapackages = datapackages_and_versions(zone, package, callback)
            basedoiminted_correction(zone, datapackages, callback)


INPUT *modify_prefix=False, *modify_basedoiminted=True, *package=
OUTPUT ruleExecOut
