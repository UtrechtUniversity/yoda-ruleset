"""Unit tests for the misc utils module"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
import time
from collections import namedtuple, OrderedDict
from unittest import TestCase

sys.path.append('../util')

from misc import check_data_package_system_avus, escape, human_readable_size, is_valid_uuid, last_run_time_acceptable, remove_empty_objects, split_string_list_by_total_length

# AVs of a successfully published data package, that is the first version of the package
avs_success_data_package = {
    "org_publication_accessRestriction": "Open - freely retrievable",
    "org_publication_anonymousAccess": "yes",
    "org_publication_approval_actor": "datamanager#tempZone",
    "org_publication_baseDOI": "10.00012/UU01-X0GU3S",
    "org_publication_baseDOIMinted": "yes",
    "org_publication_baseRandomId": "X0GU3S",
    "org_publication_combiJsonPath": "/tempZone/yoda/publication/ICGVFV-combi.json",
    "org_publication_dataCiteJsonPath": "/tempZone/yoda/publication/ICGVFV-dataCite.json",
    "org_publication_dataCiteMetadataPosted": "yes",
    "org_publication_landingPagePath": "/tempZone/yoda/publication/ICGVFV.html",
    "org_publication_landingPageUploaded": "yes",
    "org_publication_landingPageUrl": "https://public.yoda.test/allinone/UU01/ICGVFV.html",
    "org_publication_lastModifiedDateTime": "2024-10-04T15:32:46.000000",
    "org_publication_license": "Creative Commons Attribution 4.0 International Public License",
    "org_publication_licenseUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "org_publication_manifestPath": "/tempZone/yoda/publication/ICGVFV-manifest.json",
    "org_publication_manifestUploaded": "yes",
    "org_publication_oaiUploaded": "yes",
    "org_publication_publicationDate": "2024-10-04T15:33:17.853806",
    "org_publication_randomId": "ICGVFV",
    "org_publication_status": "OK",
    "org_publication_submission_actor": "researcher#tempZone",
    "org_publication_vaultPackage": "/tempZone/home/vault-default-3/research-default-3[1728048679]",
    "org_publication_versionDOI": "10.00012/UU01-ICGVFV",
    "org_publication_versionDOIMinted": "yes",
}

avs_success_data_package_multiversion = {
    "org_publication_accessRestriction": "Open - freely retrievable",
    "org_publication_anonymousAccess": "yes",
    "org_publication_approval_actor": "datamanager#tempZone",
    "org_publication_baseDOI": "10.00012/UU01-X0GU3S",
    "org_publication_baseDOIMinted": "yes",
    "org_publication_baseRandomId": "X0GU3S",
    "org_publication_combiJsonPath": "/tempZone/yoda/publication/YU0JDH-combi.json",
    "org_publication_dataCiteJsonPath": "/tempZone/yoda/publication/YU0JDH-dataCite.json",
    "org_publication_dataCiteMetadataPosted": "yes",
    "org_publication_landingPagePath": "/tempZone/yoda/publication/YU0JDH.html",
    "org_publication_landingPageUploaded": "yes",
    "org_publication_landingPageUrl": "https://public.yoda.test/allinone/UU01/YU0JDH.html",
    "org_publication_lastModifiedDateTime": "2024-10-11T08:49:17.000000",
    "org_publication_license": "Custom",
    "org_publication_manifestPath": "/tempZone/yoda/publication/YU0JDH-manifest.json",
    "org_publication_manifestUploaded": "yes",
    "org_publication_oaiUploaded": "yes",
    "org_publication_previous_version": "/tempZone/home/vault-initial1/new-group01[1728550839]",
    "org_publication_publicationDate": "2024-10-11T08:50:01.812220",
    "org_publication_randomId": "YU0JDH",
    "org_publication_status": "OK",
    "org_publication_submission_actor": "datamanager#tempZone",
    "org_publication_vaultPackage": "/tempZone/home/vault-initial1/new-group01[1728629336]",
    "org_publication_versionDOI": "10.00012/UU01-YU0JDH",
    "org_publication_versionDOIMinted": "yes"
}

avs_success_data_package_multiversion_first = {
    "org_publication_accessRestriction": "Open - freely retrievable",
    "org_publication_anonymousAccess": "yes",
    "org_publication_approval_actor": "datamanager#tempZone",
    "org_publication_baseDOI": "10.00012/UU01-X0GU3S",
    "org_publication_baseDOIMinted": "yes",
    "org_publication_baseRandomId": "X0GU3S",
    "org_publication_combiJsonPath": "/tempZone/yoda/publication/T8D8QU-combi.json",
    "org_publication_dataCiteJsonPath": "/tempZone/yoda/publication/T8D8QU-dataCite.json",
    "org_publication_dataCiteMetadataPosted": "yes",
    "org_publication_landingPagePath": "/tempZone/yoda/publication/T8D8QU.html",
    "org_publication_landingPageUploaded": "yes",
    "org_publication_landingPageUrl": "https://public.yoda.test/allinone/UU01/T8D8QU.html",
    "org_publication_lastModifiedDateTime": "2024-10-10T09:06:05.000000",
    "org_publication_license": "Creative Commons Attribution 4.0 International Public License",
    "org_publication_licenseUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "org_publication_manifestPath": "/tempZone/yoda/publication/T8D8QU-manifest.json",
    "org_publication_manifestUploaded": "yes",
    "org_publication_next_version": "/tempZone/home/vault-initial1/new-group01[1728545387]",
    "org_publication_oaiUploaded": "yes",
    "org_publication_publicationDate": "2024-10-10T09:06:02.177810",
    "org_publication_randomId": "T8D8QU",
    "org_publication_status": "OK",
    "org_publication_submission_actor": "datamanager#tempZone",
    "org_publication_vaultPackage": "/tempZone/home/vault-initial1/new-group01[1728543897]",
    "org_publication_versionDOI": "10.00012/UU01-T8D8QU",
    "org_publication_versionDOIMinted": "yes",
}

# From avu.py
Avu = namedtuple('Avu', list('avu'))
Avu.attr  = Avu.a
Avu.value = Avu.v
Avu.unit  = Avu.u


class UtilMiscTest(TestCase):

    def test_check_data_package_system_avus(self):
        # Success
        avs = avs_success_data_package
        avus_success = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_success)
        self.assertTrue(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 0)

        # Success, extra optional avu
        avs['org_publication_baseDOIAvailable'] = 'yes'
        avus_success = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_success)
        self.assertTrue(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 0)
        del avs['org_publication_baseDOIAvailable']

        # Missing license Uri for non-custom license
        del avs['org_publication_licenseUri']
        avus_missing_license_uri = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_missing_license_uri)
        self.assertFalse(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 1)
        self.assertTrue(len(result['unexpected_avus']) == 0)

        # Custom license, no license Uri (happy flow)
        avs['org_publication_license'] = "Custom"
        avus_custom_license = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_custom_license)
        self.assertTrue(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 0)

        # Unexpected
        avs['org_publication_userAddedSomethingWeird'] = "yodayoda:)"
        avus_unexpected = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_unexpected)
        self.assertTrue(result['no_missing_avus'])
        self.assertFalse(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 1)

        # Missing and unexpected
        del avs['org_publication_landingPagePath']
        avus_missing_unexpected = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_missing_unexpected)
        self.assertFalse(result['no_missing_avus'])
        self.assertFalse(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 1)
        self.assertTrue(len(result['unexpected_avus']) == 1)

        # Missing
        del avs['org_publication_userAddedSomethingWeird']
        avus_missing = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_missing)
        self.assertFalse(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 1)
        self.assertTrue(len(result['unexpected_avus']) == 0)

        # Success, latest version of a publication
        avs = avs_success_data_package_multiversion
        avus_success = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_success)
        self.assertTrue(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 0)

        # Success, first version of a publication that has had other versions
        avs = avs_success_data_package_multiversion_first
        avus_success = [Avu(attr, val, "") for attr, val in avs.items()]
        result = check_data_package_system_avus(avus_success)
        self.assertTrue(result['no_missing_avus'])
        self.assertTrue(result['no_unexpected_avus'])
        self.assertTrue(len(result['missing_avus']) == 0)
        self.assertTrue(len(result['unexpected_avus']) == 0)

    def test_last_run_time_acceptable(self):
        """Test the last run time for copy to vault"""
        # No last run time (job hasn't been tried before)
        found = False
        last_run = 1
        self.assertEqual(last_run_time_acceptable(found, last_run, 300), True)

        # Last run time greater than the backoff, so can run
        now = int(time.time())
        found = True
        copy_backoff_time = 300
        last_run = now - copy_backoff_time - 1
        self.assertEqual(last_run_time_acceptable(found, last_run, copy_backoff_time), True)

        # Last run time more recent than the backoff, so should not run
        found = True
        copy_backoff_time = 300
        last_run = now
        self.assertEqual(last_run_time_acceptable(found, int(time.time()), copy_backoff_time), False)

    def test_human_readable_size(self):
        output = human_readable_size(0)
        self.assertEqual(output, "0 B")
        output = human_readable_size(1024)
        self.assertEqual(output, "1.0 KiB")
        output = human_readable_size(1048576)
        self.assertEqual(output, "1.0 MiB")
        output = human_readable_size(26843550000)
        self.assertEqual(output, "25.0 GiB")
        output = human_readable_size(989560500000000)
        self.assertEqual(output, "900.0 TiB")
        output = human_readable_size(112590000000000000)
        self.assertEqual(output, "100.0 PiB")
        output = human_readable_size(3931462330709348188)
        self.assertEqual(output, "3.41 EiB")

    def test_remove_empty_objects(self):
        d = OrderedDict({"key1": None, "key2": "", "key3": {}, "key4": []})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({}))
        d = OrderedDict({"key1": "value1", "key2": {"key1": None, "key2": "", "key3": {}, "key4": []}})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1"}))
        d = OrderedDict({"key1": "value1", "key2": {"key1": None, "key2": "", "key3": {}, "key4": [], "key5": "value5"}})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1", "key2": {"key5": "value5"}}))
        d = OrderedDict({"key1": "value1", "key2": [{}]})
        self.assertDictEqual(remove_empty_objects(d), OrderedDict({"key1": "value1"}))

    def test_split_string_list_by_total_length(self):
        # Items don't exceed maximum length
        self.assertEqual(split_string_list_by_total_length(["abc", "def", "ghi"], 10),
                         [["abc", "def", "ghi"]])
        # Items exceed maximum length
        self.assertEqual(split_string_list_by_total_length(["abc", "def", "ghi", "jkl"], 10),
                         [["abc", "def", "ghi"], ["jkl"]])
        # Items don't exceed maximum length with additional length
        self.assertEqual(split_string_list_by_total_length(["abc", "def", "ghi"], 15, add_item_length=2),
                         [["abc", "def", "ghi"]])
        # Items exceed maximum length with additional length
        self.assertEqual(split_string_list_by_total_length(["abc", "def", "ghi"], 14, add_item_length=2),
                         [["abc", "def"], ["ghi"]])
        # Single item exceeds maximum length
        self.assertEqual(split_string_list_by_total_length(["abcabcabcabcabcabcabc", "def", "ghi"], 15),
                         [["abcabcabcabcabcabcabc"], ["def", "ghi"]])
        # Single item exceeds maximum length and throws Exception
        with self.assertRaises(Exception):  # noqa B107  / Ruff does not permit asserting exceptions in unit tests
            split_string_list_by_total_length(["abcabcabcabcabcabcabc", "def", "ghi"], 15, raise_exception_exceed=True)

    def test_escape(self):
        # Strings without single quotes are unchanged.
        self.assertEqual(escape(""), "")
        self.assertEqual(escape("research-foo"), "research-foo")
        self.assertEqual(escape("/tempZone/home/research-foo"), "/tempZone/home/research-foo")
        # Single quotes are doubled
        self.assertEqual(escape("Muad'dib"), "Muad''dib")
        self.assertEqual(escape("a'b'c"), "a''b''c")
        self.assertEqual(escape("''"), "''''")
        self.assertEqual(escape("' OR '1'='1"), "'' OR ''1''=''1")
        # Only single quotes are escaped; other characters (incl. double quotes and
        # backslashes) are left untouched.
        self.assertEqual(escape('a"b'), 'a"b')
        self.assertEqual(escape("a\\b"), "a\\b")
        self.assertEqual(escape("100%_value"), "100%_value")

    def test_is_valid_uuid(self):
        # Canonical lowercase UUID version 4 is accepted.
        self.assertTrue(is_valid_uuid("f47ac10b-58cc-4372-a567-0e02b2c3d479"))
        self.assertFalse(is_valid_uuid("F47AC10B-58CC-4372-A567-0E02B2C3D479"))
        # Non-version-4 UUIDs are rejected (version nibble is not 4).
        self.assertFalse(is_valid_uuid("f47ac10b-58cc-1372-a567-0e02b2c3d479"))
        self.assertFalse(is_valid_uuid("{f47ac10b-58cc-4372-a567-0e02b2c3d479}"))
        self.assertFalse(is_valid_uuid("urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479"))
        self.assertFalse(is_valid_uuid(""))
        self.assertFalse(is_valid_uuid("not-a-uuid"))
        self.assertFalse(is_valid_uuid("f47ac10b58cc4372a5670e02b2c3d479"))
        self.assertFalse(is_valid_uuid(None))
