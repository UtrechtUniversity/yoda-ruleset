# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_group_import import GroupImportTest
from test_intake import IntakeTest
from test_revisions import RevisionTest
from test_util_misc import UtilMiscTest
from test_util_pathutil import UtilPathutilTest
from test_util_yoda_names import UtilYodaNamesTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(GroupImportTest))
    test_suite.addTest(makeSuite(IntakeTest))
    test_suite.addTest(makeSuite(RevisionTest))
    test_suite.addTest(makeSuite(UtilMiscTest))
    test_suite.addTest(makeSuite(UtilPathutilTest))
    test_suite.addTest(makeSuite(UtilYodaNamesTest))
    return test_suite
