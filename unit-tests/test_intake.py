# -*- coding: utf-8 -*-

"""Unit tests for the intake module
"""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import sys
from unittest import TestCase

sys.path.append('..')

from intake_utils import dataset_make_id, dataset_parse_id, intake_extract_tokens, intake_extract_tokens_from_name, intake_scan_get_metadata_update, intake_tokens_identify_dataset


class IntakeTest(TestCase):

    def test_intake_tokens_identify_dataset(self):
        empty_data = dict()
        self.assertFalse(intake_tokens_identify_dataset(empty_data))
        missing_key_data = {"wave": "1", "pseudocode": "2"}
        self.assertFalse(intake_tokens_identify_dataset(missing_key_data))
        missing_value_data = {"wave": "1", "pseudocode": "2", "experiment_type": ""}
        self.assertFalse(intake_tokens_identify_dataset(missing_value_data))
        complete_data = {"wave": "1", "pseudocode": "2", "experiment_type": "3"}
        self.assertTrue(intake_tokens_identify_dataset(complete_data))

    def test_intake_extract_tokens(self):
        no_token_data = intake_extract_tokens(None, "")
        self.assertEquals(len(no_token_data), 0)
        wave_data = intake_extract_tokens(None, "20w")
        self.assertEquals(len(wave_data), 1)
        self.assertEquals(wave_data["wave"], "20w")
        et_data = intake_extract_tokens(None, "chantigap")
        self.assertEquals(len(et_data), 1)
        self.assertEquals(et_data["experiment_type"], "chantigap")
        pseudocode_data = intake_extract_tokens(None, "B12345")
        self.assertEquals(len(pseudocode_data), 1)
        self.assertEquals(pseudocode_data["pseudocode"], "B12345")
        version_data = intake_extract_tokens(None, "VerABC")
        self.assertEquals(len(version_data), 1)
        self.assertEquals(version_data["version"],  "ABC")

    def test_intake_extract_tokens_from_name(self):
        buffer = dict()
        output = intake_extract_tokens_from_name(None, "20w_chantigap_B12345_VerABC.txt", buffer)
        self.assertEquals(len(output), 4)
        self.assertEquals(output["wave"], "20w")
        self.assertEquals(output["experiment_type"], "chantigap")
        self.assertEquals(output["version"], "ABC")
        self.assertEquals(output["pseudocode"], "B12345")

    def test_intake_scan_get_metadata_update_coll_in_dataset(self):
        parent_path = "/foo/bar/chantigap_10w_B12345"
        path = parent_path + "/chantigap_20w_B12346"
        complete_metadata = {"wave": "1",
                             "pseudocode": "2",
                             "experiment_type": "3",
                             "version": "Raw",
                             "directory": parent_path,
                             "dataset_id": "4",
                             "dataset_toplevel": "5"}

        output = intake_scan_get_metadata_update(None, path, True, True, complete_metadata)
        self.assertEquals(output["in_dataset"], True)
        self.assertEquals(len(output["new_metadata"]), 6)
        self.assertEquals(output["new_metadata"]["directory"], parent_path)
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["pseudocode"], "2")
        self.assertEquals(output["new_metadata"]["experiment_type"], "3")
        self.assertEquals(output["new_metadata"]["version"], "Raw")
        self.assertEquals(output["new_metadata"]["dataset_id"], "4")
        self.assertTrue("dataset_toplevel" not in output["new_metadata"])

    def test_intake_scan_get_metadata_update_coll_out_dataset_complete(self):
        incomplete_metadata = {"wave": "1", "pseudocode": "2"}
        path = "/foo/bar/chantigap_10w_B12345/chantigap_B12346"
        output = intake_scan_get_metadata_update(None, path, True, False, incomplete_metadata)
        self.assertEquals(output["in_dataset"], True)
        self.assertEquals(len(output["new_metadata"]), 7)
        self.assertEquals(output["new_metadata"]["directory"], path)
        self.assertEquals(output["new_metadata"]["dataset_toplevel"], dataset_make_id(output["new_metadata"]))
        self.assertEquals(output["new_metadata"]["dataset_id"], dataset_make_id(output["new_metadata"]))
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["version"], "Raw")
        self.assertEquals(output["new_metadata"]["pseudocode"], "B12346")
        self.assertEquals(output["new_metadata"]["experiment_type"], "chantigap")

    def test_intake_scan_get_metadata_update_coll_out_dataset_incomplete(self):
        incomplete_metadata = {"wave": "1"}
        path = "/foo/bar/chantigap_10w_B12345/B12346"
        output = intake_scan_get_metadata_update(None, path, True, False, incomplete_metadata)
        self.assertEquals(output["in_dataset"], False)
        self.assertEquals(len(output["new_metadata"]), 2)
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["pseudocode"], "B12346")

    def test_intake_scan_get_metadata_update_do_in_dataset(self):
        complete_metadata = {"wave": "1",
                             "pseudocode": "2",
                             "experiment_type": "3",
                             "version": "Raw",
                             "dataset_id": "4",
                             "dataset_toplevel": "5",
                             "directory": "6"}
        path = "/foo/bar/chantigap_10w_B12345/chantigap_20w_B12346.txt"
        output = intake_scan_get_metadata_update(None, path, False, True, complete_metadata)
        self.assertEquals(output["in_dataset"], True)
        self.assertEquals(len(output["new_metadata"]), 6)
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["pseudocode"], "2")
        self.assertEquals(output["new_metadata"]["experiment_type"], "3")
        self.assertEquals(output["new_metadata"]["version"], "Raw")
        self.assertEquals(output["new_metadata"]["dataset_id"], "4")
        self.assertTrue("dataset_toplevel" not in output["new_metadata"])

    def test_intake_scan_get_metadata_update_do_out_dataset_complete(self):
        incomplete_metadata = {"wave": "1", "pseudocode": "2"}
        path = "/foo/bar/chantigap_10w_B12345/chantigap_B12346.txt"
        coll = os.path.dirname(path)
        output = intake_scan_get_metadata_update(None, path, False, False, incomplete_metadata)
        self.assertEquals(output["in_dataset"], True)
        self.assertEquals(len(output["new_metadata"]), 7)
        self.assertEquals(output["new_metadata"]["directory"], coll)
        self.assertEquals(output["new_metadata"]["dataset_id"], dataset_make_id(output["new_metadata"]))
        self.assertEquals(output["new_metadata"]["dataset_toplevel"], dataset_make_id(output["new_metadata"]))
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["version"], "Raw")
        self.assertEquals(output["new_metadata"]["pseudocode"], "B12346")
        self.assertEquals(output["new_metadata"]["experiment_type"], "chantigap")

    def test_intake_scan_get_metadata_update_do_out_dataset_incomplete(self):
        incomplete_metadata = {"wave": "1"}
        path = "/foo/bar/chantigap_10w_B12345/B12346.txt"
        output = intake_scan_get_metadata_update(None, path, False, False, incomplete_metadata)
        self.assertEquals(output["in_dataset"], False)
        self.assertEquals(len(output["new_metadata"]), 2)
        self.assertEquals(output["new_metadata"]["wave"], "1")
        self.assertEquals(output["new_metadata"]["pseudocode"], "B12346")

    def test_dataset_make_id(self):
        input = {"wave": "20w",
                 "experiment_type": "echo",
                 "pseudocode": "B12345",
                 "version": "Raw",
                 "directory": "/foo/bar/baz"}
        self.assertEquals(dataset_make_id(input),
                          "20w\techo\tB12345\tRaw\t/foo/bar/baz")

    def test_dataset_parse_id(self):
        input = "20w\techo\tB12345\tRaw\t/foo/bar/baz"
        output = dataset_parse_id(input)
        self.assertEquals(output.get("wave"), "20w")
        self.assertEquals(output.get("experiment_type"), "echo")
        self.assertEquals(output.get("pseudocode"), "B12345")
        self.assertEquals(output.get("version"), "Raw")
        self.assertEquals(output.get("directory"), "/foo/bar/baz")
