# -*- coding: utf-8 -*-
"""Miscellaneous util functions."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import math
import time
from collections import OrderedDict

import constants


def check_data_package_system_avus(extracted_avus):
    """
    Checks whether a data package has the expected system AVUs that start with constants.UUORGMETADATAPREFIX (i.e, 'org_').
    This function compares the AVUs of the provided data package against a set of ground truth AVUs derived from
    a successfully published data package.

    :param extracted_avus: AVUs of the data package in AVU form

    :returns:            Dictionary of the results of the check
    """
    # Filter those starting with 'org_publication'
    extracted_avs = {}
    for m in extracted_avus:
        if m.attr.startswith(constants.UUORGMETADATAPREFIX + 'publication_'):
            extracted_avs[m.attr] = m.value
    extracted_attrs = set(extracted_avs.keys())

    # Define the set of ground truth AVUs
    avu_names_suffix = {
        'approval_actor', 'randomId',
        'versionDOI', 'dataCiteJsonPath', 'license',
        'anonymousAccess', 'versionDOIMinted',
        'accessRestriction', 'landingPagePath',
        'publicationDate',
        'vaultPackage', 'submission_actor', 'status',
        'lastModifiedDateTime', 'combiJsonPath',
        'landingPageUploaded', 'oaiUploaded',
        'landingPageUrl', 'dataCiteMetadataPosted'
    }

    # If the license is not Custom, it must have a licenseUri
    if constants.UUORGMETADATAPREFIX + 'publication_license' in extracted_attrs:
        if extracted_avs[constants.UUORGMETADATAPREFIX + 'publication_license'] != "Custom":
            avu_names_suffix.add('licenseUri')

    # Define additional set of AVUs with more than one version of publication
    avu_names_version_suffix = {
        'previous_version', 'baseDOI', 'baseRandomId',
        'baseDOIMinted'
    }

    # Define additional set of AVUs expected for the first version of a publication, when there are multiple versions
    avu_names_first_version_suffix = {
        'baseRandomId', 'baseDOI', 'next_version'
    }

    # for the second version, all we need is next_version in addition to avu_names_version_suffix
    avu_names_previous_version_suffix = {'next_version'}

    # optional avus
    avu_names_optional_suffix = {
        'versionDOIAvailable', 'baseDOIAvailable'
    }

    combined_avu_names_suffix = avu_names_suffix

    if constants.UUORGMETADATAPREFIX + 'publication_previous_version' in extracted_attrs:
        combined_avu_names_suffix.update(avu_names_version_suffix)
        if constants.UUORGMETADATAPREFIX + 'publication_next_version' in extracted_attrs:
            combined_avu_names_suffix.update(avu_names_previous_version_suffix)
    elif constants.UUORGMETADATAPREFIX + 'publication_next_version' in extracted_attrs:
        combined_avu_names_suffix.update(avu_names_first_version_suffix)

    ground_truth_avus = {"{}publication_{}".format(constants.UUORGMETADATAPREFIX, name) for name in combined_avu_names_suffix}
    combined_avu_names_suffix.update(avu_names_optional_suffix)
    ground_truth_avus_with_optional = {"{}publication_{}".format(constants.UUORGMETADATAPREFIX, name) for name in combined_avu_names_suffix}
    # Find missing and unexpected AVUs
    missing_avus = ground_truth_avus - extracted_attrs
    unexpected_avus = extracted_attrs - ground_truth_avus_with_optional

    results = {
        'no_missing_avus': not bool(missing_avus),
        'missing_avus': list(missing_avus),
        'no_unexpected_avus': not bool(unexpected_avus),
        'unexpected_avus': list(unexpected_avus)
    }

    return results


def last_run_time_acceptable(found, last_run, config_backoff_time):
    """Return whether the last run time is acceptable to continue with task."""
    now = int(time.time())

    if found:
        # Too soon to run
        if now < last_run + config_backoff_time:
            return False

    return True


def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_name = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '{} {}'.format(s, size_name[i])


def remove_empty_objects(d):
    """Remove empty objects (None, '', {}, []) from OrderedDict."""
    if isinstance(d, dict):
        # Create OrderedDict to maintain order.
        cleaned_dict = OrderedDict()
        for k, v in d.items():
            # Recursively remove empty objects.
            cleaned_value = remove_empty_objects(v)
            # Only add non-empty values.
            if cleaned_value not in (None, '', {}, []):
                cleaned_dict[k] = cleaned_value
        return cleaned_dict
    elif isinstance(d, list):
        # Clean lists by filtering out empty objects.
        return [remove_empty_objects(item) for item in d if remove_empty_objects(item) not in (None, '', {}, [])]
    else:
        # Return the value because it is not a dict or list.
        return d
