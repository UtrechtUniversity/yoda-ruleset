# -*- coding: utf-8 -*-
"""Unit tests for the pathutil utils module"""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('../util')

from pathutil import basename, chop, dirname, info, Space


class UtilPathutilTest(TestCase):

    def test_chop(self):
        output = chop("")
        self.assertEquals(output, ('/', ''))
        output = chop("/")
        self.assertEquals(output, ('/', ''))
        output = chop("/tempZone")
        self.assertEquals(output, ('', 'tempZone'))
        output = chop("/tempZone/yoda")
        self.assertEquals(output, ('/tempZone', 'yoda'))
        output = chop("/tempZone/home")
        self.assertEquals(output, ('/tempZone', 'home'))
        output = chop("/tempZone/home/rods")
        self.assertEquals(output, ('/tempZone/home', 'rods'))
        output = chop("/tempZone/home/research-test")
        self.assertEquals(output, ('/tempZone/home', 'research-test'))
        output = chop("/tempZone/home/research-test/test")
        self.assertEquals(output, ('/tempZone/home/research-test', 'test'))
        output = chop("/tempZone/home/research-test/test/file.txt")
        self.assertEquals(output, ('/tempZone/home/research-test/test', 'file.txt'))

    def test_dirname(self):
        output = dirname("")
        self.assertEquals(output, '/')
        output = dirname("/")
        self.assertEquals(output, '/')
        output = dirname("/tempZone")
        self.assertEquals(output, '')
        output = dirname("/tempZone/yoda")
        self.assertEquals(output, '/tempZone')
        output = dirname("/tempZone/home")
        self.assertEquals(output, '/tempZone')
        output = dirname("/tempZone/home/rods")
        self.assertEquals(output, '/tempZone/home')
        output = dirname("/tempZone/home/research-test")
        self.assertEquals(output, '/tempZone/home')
        output = dirname("/tempZone/home/research-test/test")
        self.assertEquals(output, '/tempZone/home/research-test')
        output = dirname("/tempZone/home/research-test/test/file.txt")
        self.assertEquals(output, '/tempZone/home/research-test/test')

    def test_basename(self):
        output = basename("")
        self.assertEquals(output, '')
        output = basename("/")
        self.assertEquals(output, '')
        output = basename("/tempZone")
        self.assertEquals(output, 'tempZone')
        output = basename("/tempZone/yoda")
        self.assertEquals(output, 'yoda')
        output = basename("/tempZone/home")
        self.assertEquals(output, 'home')
        output = basename("/tempZone/home/rods")
        self.assertEquals(output, 'rods')
        output = basename("/tempZone/home/research-test")
        self.assertEquals(output, 'research-test')
        output = basename("/tempZone/home/research-test/test")
        self.assertEquals(output, 'test')
        output = basename("/tempZone/home/research-test/test/file.txt")
        self.assertEquals(output, 'file.txt')

    def test_info(self):
        output = info("")
        self.assertEquals(output, (Space.OTHER, '', '', ''))
        output = info("/")
        self.assertEquals(output, (Space.OTHER, '', '', ''))
        output = info("/tempZone")
        self.assertEquals(output, (Space.OTHER, 'tempZone', '', ''))
        output = info("/tempZone/yoda")
        self.assertEquals(output, (Space.OTHER, 'tempZone', '', 'yoda'))
        output = info("/tempZone/home")
        self.assertEquals(output, (Space.OTHER, 'tempZone', '', 'home'))
        output = info("/tempZone/home/rods")
        self.assertEquals(output, (Space.OTHER, 'tempZone', 'rods', ''))
        output = info("/tempZone/home/research-test")
        self.assertEquals(output, (Space.RESEARCH, 'tempZone', 'research-test', ''))
        output = info("/tempZone/home/research-test/test")
        self.assertEquals(output, (Space.RESEARCH, 'tempZone', 'research-test', 'test'))
        output = info("/tempZone/home/research-test/test/file.txt")
        self.assertEquals(output, (Space.RESEARCH, 'tempZone', 'research-test', 'test/file.txt'))
        output = info("/tempZone/home/vault-test")
        self.assertEquals(output, (Space.VAULT, 'tempZone', 'vault-test', ''))
        output = info("/tempZone/home/datamanager-test")
        self.assertEquals(output, (Space.DATAMANAGER, 'tempZone', 'datamanager-test', ''))
        output = info("/tempZone/home/deposit-test")
        self.assertEquals(output, (Space.DEPOSIT, 'tempZone', 'deposit-test', ''))
        output = info("/tempZone/home/intake-test")
        self.assertEquals(output, (Space.INTAKE, 'tempZone', 'intake-test', ''))
        output = info("/tempZone/home/grp-intake-test")
        self.assertEquals(output, (Space.INTAKE, 'tempZone', 'grp-intake-test', ''))
        output = info("/tempZone/home/datarequests-test")
        self.assertEquals(output, (Space.DATAREQUEST, 'tempZone', 'datarequests-test', ''))
