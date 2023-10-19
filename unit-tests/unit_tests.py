# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_intake import IntakeTest
from test_util_misc import UtilMiscTest
from test_util_pathutil import UtilPathutilTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(IntakeTest))
    test_suite.addTest(makeSuite(UtilMiscTest))
    test_suite.addTest(makeSuite(UtilPathutilTest))
    return test_suite
