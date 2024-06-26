# -*- coding: utf-8 -*-
"""Unit tests for the policies"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from policies_utils import _is_safe_genquery_inp


class PoliciesTest(TestCase):

    def test_is_safe_genquery_inp(self):
        # Queries that do not pose any problems
        # select D_DATA_ID where DATA_NAME = 'rods' and COLL_NAME = '/tempZone/home'
        selectInp = {401: 1}
        sqlCondInp = [(403, "= 'rods'"), (501, "= '/tempZone/home'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select D_CREATE_TIME, D_MODIFY_TIME, DATA_MODE, D_RESC_ID, D_DATA_ID, DATA_SIZE, D_OWNER_NAME, D_OWNER_ZONE, D_REPL_STATUS, D_DATA_CHECKSUM where COLL_NAME ='/tempZone/home' and DATA_NAME ='rods'
        selectInp = {419: 1, 420: 1, 421: 1, 423: 1, 401: 1, 407: 1, 411: 1, 412: 1, 413: 1, 415: 1}
        sqlCondInp = [(501, "='/tempZone/home'"), (403, "='rods'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select COLL_INFO2, COLL_ID, COLL_NAME, COLL_OWNER_NAME, COLL_OWNER_ZONE, COLL_CREATE_TIME, COLL_MODIFY_TIME, COLL_TYPE, COLL_INFO1 where COLL_NAME ='/tempZone/home/rods'
        selectInp = {512: 1, 500: 1, 501: 1, 503: 1, 504: 1, 508: 1, 509: 1, 510: 1, 511: 1}
        sqlCondInp = [(501, "='/tempZone/home/rods'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select D_CREATE_TIME, D_MODIFY_TIME, DATA_MODE, D_DATA_ID, DATA_NAME, COLL_NAME, DATA_SIZE where COLL_NAME  = '/tempZone/home/rods'
        selectInp = {419: 1, 420: 1, 421: 1, 401: 1, 403: 1, 501: 1, 407: 1}
        sqlCondInp = [(501, " = '/tempZone/home/rods'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select ZONE_CONNECTION, ZONE_COMMENT, ZONE_NAME, ZONE_TYPE where
        selectInp = {104: 1, 105: 1, 102: 1, 103: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_COLL_ATTR_VALUE where COLL_NAME = '/a/b/c'
        selectInp = {611: 1}
        sqlCondInp = [(501, "= '/a/b/c'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_COLL_ATTR_VALUE, COLL_NAME where
        selectInp = {611: 1, 501: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_DATA_ATTR_VALUE, DATA_NAME where
        selectInp = {601: 1, 403: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_RESC_ATTR_VALUE, RESC_NAME where
        selectInp = {631: 1, 302: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_USER_ATTR_VALUE, USER_NAME where
        selectInp = {641: 1, 202: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_DATA_ATTR_VALUE where DATA_NAME = 'test.dat'
        selectInp = {601: 1}
        sqlCondInp = [(403, "= 'test.dat'")]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_DATA_ATTR_VALUE, COLL_NAME where
        selectInp = {601: 1, 501: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # Query for collection metadata without collection column selected or collection condition
        # select META_COLL_ATTR_VALUE where
        selectInp = {611: 1}
        sqlCondInp = []
        self.assertFalse(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # Query for data object metadata without dataobject column selected or data object condition
        # select META_DATA_ATTR_VALUE where
        selectInp = {601: 1}
        sqlCondInp = []
        self.assertFalse(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # Query for resource metadata without any other column selected or condition
        # select META_RESC_ATTR_VALUE where
        selectInp = {631: 1}
        sqlCondInp = []
        self.assertFalse(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # Query for user metadata without any other column selected or condition
        selectInp = {641: 1}
        sqlCondInp = []
        self.assertFalse(_is_safe_genquery_inp(selectInp, sqlCondInp))
