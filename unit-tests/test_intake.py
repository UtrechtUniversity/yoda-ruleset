# -*- coding: utf-8 -*-

"""Unit tests for the intake module
"""

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from intake_utils import intake_extract_tokens, intake_extract_tokens_from_name, intake_tokens_identify_dataset


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
        output = intake_extract_tokens_from_name(None, None, "20w_chantigap_B12345_VerABC.txt", None, buffer)
        self.assertEquals(len(output), 4)
        self.assertEquals(output["wave"], "20w")
        self.assertEquals(output["experiment_type"], "chantigap")
        self.assertEquals(output["version"], "ABC")
        self.assertEquals(output["pseudocode"], "B12345")
