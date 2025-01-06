# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_group_import import GroupImportTest
from test_intake import IntakeTest
from test_policies import PoliciesTest
from test_revisions import RevisionTest
from test_schema_transformations import CorrectifyIsniTest, CorrectifyOrcidTest, CorrectifyScopusTest
from test_util_misc import UtilMiscTest
from test_util_pathutil import UtilPathutilTest
from test_util_yoda_names import UtilYodaNamesTest
from test_vault import VaultTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(CorrectifyIsniTest))
    test_suite.addTest(makeSuite(CorrectifyOrcidTest))
    test_suite.addTest(makeSuite(CorrectifyScopusTest))
    test_suite.addTest(makeSuite(GroupImportTest))
    test_suite.addTest(makeSuite(IntakeTest))
    test_suite.addTest(makeSuite(PoliciesTest))
    test_suite.addTest(makeSuite(RevisionTest))
    test_suite.addTest(makeSuite(UtilMiscTest))
    test_suite.addTest(makeSuite(UtilPathutilTest))
    test_suite.addTest(makeSuite(UtilYodaNamesTest))
    test_suite.addTest(makeSuite(VaultTest))
    return test_suite
