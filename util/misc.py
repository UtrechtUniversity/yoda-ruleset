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

    :param extracted_avus: AVUs of the data package

    :returns:            Dictionary of the results of the check
    """
    # Filter those starting with 'org_'
    extracted_avus = {m.attr for m in extracted_avus if m.attr.startswith(constants.UUORGMETADATAPREFIX + 'publication_')}

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

    return results


def last_run_time_acceptable(coll, found, last_run, config_backoff_time):
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
        # Return the value abecause it is not a dict or list.
        return d
