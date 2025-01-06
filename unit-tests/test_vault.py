"""Unit tests for the vault functions"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from vault_utils import get_copy_folder_to_vault_irsync_command


class VaultTest(TestCase):

    def test_get_copy_folder_to_vault_irsync_command_with_vault_resc(self):
        output = get_copy_folder_to_vault_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc", "vaultResc", True)
        self.assertEqual(output, ["irsync", "-rK", "-R", "vaultResc", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])

    def test_get_copy_folder_to_vault_irsync_command_without_vault_resc(self):
        output = get_copy_folder_to_vault_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc", None, True)
        self.assertEqual(output, ["irsync", "-rK", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])

    def test_get_copy_folder_to_vault_irsync_command_no_multithreading(self):
        output = get_copy_folder_to_vault_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc", "vaultResc", False)
        self.assertEqual(output, ["irsync", "-rK", "-R", "vaultResc", "-N", "0", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])
