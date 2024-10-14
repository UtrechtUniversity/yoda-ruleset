# -*- coding: utf-8 -*-
"""Unit tests for the misc utils module"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
import time
from collections import namedtuple, OrderedDict
from unittest import TestCase

sys.path.append('../util')

from misc import check_data_package_system_avus, human_readable_size, last_run_time_acceptable, remove_empty_objects

avs_success_data_package = {
    "org_publication_accessRestriction": "Open - freely retrievable",
    "org_publication_anonymousAccess": "yes",
    "org_publication_approval_actor": "datamanager#tempZone",
    "org_publication_combiJsonPath": "/tempZone/yoda/publication/ICGVFV-combi.json",
    "org_publication_dataCiteJsonPath": "/tempZone/yoda/publication/ICGVFV-dataCite.json",
    "org_publication_dataCiteMetadataPosted": "yes",
    "org_publication_landingPagePath": "/tempZone/yoda/publication/ICGVFV.html",
    "org_publication_landingPageUploaded": "yes",
    "org_publication_landingPageUrl": "https://public.yoda.test/allinone/UU01/ICGVFV.html",
    "org_publication_lastModifiedDateTime": "2024-10-04T15:32:46.000000",
    "org_publication_license": "Creative Commons Attribution 4.0 International Public License",
    "org_publication_licenseUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "org_publication_oaiUploaded": "yes",
    "org_publication_publicationDate": "2024-10-04T15:33:17.853806",
    "org_publication_randomId": "ICGVFV",
    "org_publication_status": "OK",
    "org_publication_submission_actor": "researcher#tempZone",
    "org_publication_vaultPackage": "/tempZone/home/vault-default-3/research-default-3[1728048679]",
    "org_publication_versionDOI": "10.00012/UU01-ICGVFV",
    "org_publication_versionDOIMinted": "yes",
}
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

    def test_last_run_time_acceptable(self):
        """Test the last run time for copy to vault"""
        # No last run time (job hasn't be tried before)
        found = False
        last_run = 1
        self.assertEqual(last_run_time_acceptable("b", found, last_run, 300), True)

        # Last run time greater than the backoff, so can run
        now = int(time.time())
        found = True
        copy_backoff_time = 300
        last_run = now - copy_backoff_time - 1
        self.assertEqual(last_run_time_acceptable("b", found, last_run, copy_backoff_time), True)

        # Last run time more recent than the backoff, so should not run
        found = True
        copy_backoff_time = 300
        last_run = now
        self.assertEqual(last_run_time_acceptable("b", found, int(time.time()), copy_backoff_time), False)

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
