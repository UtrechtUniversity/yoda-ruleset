"""Miscellaneous util functions."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import math
import time
import uuid
from collections import OrderedDict
from typing import Dict, List

import constants


def check_data_package_system_avus(extracted_avus: Dict) -> Dict:
    """Checks whether a data package has the expected system AVUs that start with constants.UUORGMETADATAPREFIX (i.e, 'org_').

    This function compares the AVUs of the provided data package against a set of ground truth AVUs derived from
    a successfully published data package.

    :param extracted_avus: AVUs of the data package in AVU form

    :returns: Dictionary of the results of the check
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
        'landingPageUrl', 'dataCiteMetadataPosted',
        'manifestPath', 'manifestUploaded',
        'baseDOI', 'baseDOIMinted', 'baseRandomId'
    }

    # If the license is not Custom, it must have a licenseUri
    if constants.UUORGMETADATAPREFIX + 'publication_license' in extracted_attrs:
        if extracted_avs[constants.UUORGMETADATAPREFIX + 'publication_license'] != "Custom":
            avu_names_suffix.add('licenseUri')

    # Define additional set of AVUs with more than one version of publication
    avu_names_version_suffix = {'previous_version'}

    # Define additional set of AVUs expected for the first version of a publication, when there are multiple versions
    avu_names_first_version_suffix = {'next_version'}

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


def last_run_time_acceptable(found: bool, last_run: int, config_backoff_time: int) -> bool:
    """Return whether the last run time is acceptable to continue with task."""
    now = int(time.time())

    if found:
        # Too soon to run
        if now < last_run + config_backoff_time:
            return False

    return True


def human_readable_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"

    size_name = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '{} {}'.format(s, size_name[i])


def remove_empty_objects(d: Dict) -> Dict:
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


def escape(unsafe: str) -> str:
    """Escaping Special Characters for GenQuery2."""
    safe = unsafe.replace("'", "''")
    return safe


def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is a valid UUID version 4.

    :param uuid_string: String to validate as UUID 4

    :returns: Boolean indictating if string is a valid UUID
    """
    try:
        uuid_obj = uuid.UUID(uuid_string, version=4)
    except (TypeError, ValueError):
        return False

    return str(uuid_obj) == uuid_string


def split_string_list_by_total_length(string_list: List[str], max_length: int, add_item_length: int = 0, raise_exception_exceed: bool = False) -> List[List[str]]:
    """Split a list of strings into sublists where the total length of all strings
       in a sublist does not exceed the maximum length. This can be useful when you want
       to process a list of strings, but need to take into account a maximum length supported
       by iRODS (e.g. for GenQueries).

       :param string_list: List of strings to process
       :param max_length: The maximum length of each sublist in the output. By default, if a single string
                          (along with its additional item length, if applicable) exceeds the maximum length,
                          if it included in a sublist by itself.
       :param add_item_length: Additional item length. Increase the length of each string by this number.
                          This is useful if you need to add additional characters to each string when you
                          use the sublists (e.g. separator characters or quote characters)
       :param raise_exception_exceed: Raise an exception if the length of an individual string (along with
                          its additional item length) exceeds the maximum length, rather than including the
                          string in its own sublist.

       :raises Exception: if a single string in the input list plus the additional item length exceeds
                          the maximum length, so that it is not possible to strictly meet the maximum
                          length requirement. By default, such long strings are included in a sublist
                          by themselves, and no exception is raised.

       :returns: List of sublists, where each sublist is either a single string, or a list of strings
                          whose total size does not exceed the maximum length.

    """
    output: List[List[str]] = []
    current_sublist: List[str] = []
    current_length: List[int] = [0]  # In a list so that we can pass it by reference to subfunctions

    def end_of_sublist(current_sublist: List[str], current_length: List[int], output: List[List[str]]) -> None:
        if len(current_sublist) > 0:
            output.append(current_sublist.copy())
            current_sublist.clear()
            current_length[0] = 0

    def add_to_sublist(item: str, effective_length: int, current_sublist: List[str], current_length: List[int]) -> None:
        current_sublist.append(item)
        current_length[0] += effective_length

    for item in string_list:
        effective_length = len(item) + add_item_length
        if effective_length > max_length:
            if raise_exception_exceed:
                raise Exception(f"Item '{item}' exceeded maximum sublist length.")
            else:
                end_of_sublist(current_sublist, current_length, output)
                add_to_sublist(item, effective_length, current_sublist, current_length)
                end_of_sublist(current_sublist, current_length, output)
        elif current_length[0] + effective_length > max_length:
            end_of_sublist(current_sublist, current_length, output)
            add_to_sublist(item, effective_length, current_sublist, current_length)
        else:
            add_to_sublist(item, effective_length, current_sublist, current_length)

    end_of_sublist(current_sublist, current_length, output)

    return output
