# -*- coding: utf-8 -*-

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_intake import IntakeTest
from test_revisions import RevisionTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(IntakeTest))
    test_suite.addTest(makeSuite(RevisionTest))
    return test_suite
