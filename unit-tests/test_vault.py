"""Unit tests for the vault functions"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from vault_utils import get_copy_folder_to_vault_irsync_command, get_sanity_checks_results_copy_to_vault_paths


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

    def test_get_sanity_check_results_copy_to_vault_paths_ok(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo", "/tempZone/home/vault-foo")
        self.assertEqual(output, [])

    def test_get_sanity_check_results_copy_to_vault_paths_relative_source(self):
        output = get_sanity_checks_results_copy_to_vault_paths("research-foo", "/tempZone/home/vault-foo")
        self.assertEqual(output, ["Source path is not absolute."])

    def test_get_sanity_check_results_copy_to_vault_paths_relative_target(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo", "vault-foo")
        self.assertEqual(output, ["Target path is not absolute."])

    def test_get_sanity_check_results_copy_to_vault_paths_dotdot_source(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo/..", "/tempZone/home/vault-foo")
        self.assertEqual(output, ["Source path contains parent references (..)"])

    def test_get_sanity_check_results_copy_to_vault_paths_dotdot_target(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo", "/tempZone/home/../vault-foo")
        self.assertEqual(output, ["Target path contains parent references (..)"])

    def test_get_sanity_check_results_copy_to_vault_paths_wrong_source_space(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/vault-foo", "/tempZone/home/vault-foo")
        self.assertEqual(output, ["Source path not in research or deposit group."])

    def test_get_sanity_check_results_copy_to_vault_paths_wrong_target_space(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo", "/tempZone/home/deposit-foo")
        self.assertEqual(output, ["Target path not in vault group."])

    def test_get_sanity_check_results_copy_to_vault_paths_source_target_mismatch(self):
        output = get_sanity_checks_results_copy_to_vault_paths("/tempZone/home/research-foo", "/tempZone/home/vault-bar")
        self.assertEqual(output, ["Source and target group are not in same compartment."])
