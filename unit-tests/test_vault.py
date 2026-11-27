"""Unit tests for the vault functions"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import base64
import sys
from dataclasses import replace
from unittest import TestCase

sys.path.append('..')

from vault_utils import copy_to_research_denial_reason, CopyToResearchFacts, get_copy_irsync_command, get_sanity_checks_results_copy_to_research_paths, get_sanity_checks_results_copy_to_vault_paths, parse_copy_to_research_args


class VaultTest(TestCase):

    def test_get_copy_irsync_command_with_vault_resc(self):
        output = get_copy_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc/original", "vaultResc", True)
        self.assertEqual(output, ["irsync", "-rK", "-R", "vaultResc", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])

    def test_get_copy_irsync_command_without_vault_resc(self):
        output = get_copy_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc/original", None, True)
        self.assertEqual(output, ["irsync", "-rK", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])

    def test_get_copy_irsync_command_no_multithreading(self):
        output = get_copy_irsync_command("/zoneName/home/research-foo/abc", "/zoneName/home/vault-foo/abc/original", "vaultResc", False)
        self.assertEqual(output, ["irsync", "-rK", "-R", "vaultResc", "-N", "0", "i:/zoneName/home/research-foo/abc/", "i:/zoneName/home/vault-foo/abc/original"])

    def test_get_copy_irsync_command_copy_from_research_mode(self):
        output = get_copy_irsync_command("/zoneName/home/vault-foo/abc", "/zoneName/home/research-foo/abc", None, False)
        self.assertEqual(output, ["irsync", "-rK", "-N", "0", "i:/zoneName/home/vault-foo/abc/", "i:/zoneName/home/research-foo/abc"])

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

    def test_get_sanity_check_results_copy_to_research_paths_ok(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/vault-foo", "/tempZone/home/research-foo")
        self.assertEqual(output, [])

    def test_get_sanity_check_results_copy_to_research_paths_relative_source(self):
        output = get_sanity_checks_results_copy_to_research_paths("vault-foo", "/tempZone/home/research-foo")
        self.assertEqual(output, ["Source path is not absolute."])

    def test_get_sanity_check_results_copy_to_research_paths_relative_target(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/vault-foo", "research-foo")
        self.assertEqual(output, ["Target path is not absolute."])

    def test_get_sanity_check_results_copy_to_research_paths_dotdot_source(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/vault-foo/..", "/tempZone/home/research-foo")
        self.assertEqual(output, ["Source path contains parent references (..)"])

    def test_get_sanity_check_results_copy_to_research_paths_dotdot_target(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/vault-foo", "/tempZone/home/../research-foo")
        self.assertEqual(output, ["Target path contains parent references (..)"])

    def test_get_sanity_check_results_copy_to_research_paths_wrong_source_space(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/research-foo", "/tempZone/home/research-bar")
        self.assertEqual(output, ["Source path not in vault group."])

    def test_get_sanity_check_results_copy_to_research_paths_wrong_target_space(self):
        output = get_sanity_checks_results_copy_to_research_paths("/tempZone/home/vault-foo", "/tempZone/home/vault-bar")
        self.assertEqual(output, ["Target path not in research or deposit group."])


ACTOR = "alice#tempZone"
ORIGIN = "/tempZone/home/vault-foo/package[1700000000]"
RESEARCH_TARGET = "/tempZone/home/research-bar/folder/package[1700000000]"
DEPOSIT_TARGET = "/tempZone/home/deposit-pilot/research-bar[1700000001]"

# Facts for a request that the API functions would allow.
RESEARCH_FACTS = CopyToResearchFacts(origin_readable=True,
                                     actor_is_origin_datamanager=False,
                                     target_group_role="normal",
                                     target_exists=False,
                                     target_parent_exists=True,
                                     target_locked=False,
                                     target_parent_locked=False,
                                     target_has_data=False)
DEPOSIT_FACTS = replace(RESEARCH_FACTS, target_exists=True)


def b64(value):
    return base64.b64encode(value.encode()).decode()


def copy_args(origin=ORIGIN, target=RESEARCH_TARGET, receiver=ACTOR, retry="1", actor=ACTOR):
    return " ".join([actor, b64(origin), b64(target), b64(receiver), b64(retry)])


class VaultCopyToResearchPolicyTest(TestCase):

    def reason(self, facts, **kwargs):
        """Return the denial reason (None if allowed) for a request."""
        request = parse_copy_to_research_args(copy_args(**kwargs), ACTOR)
        return copy_to_research_denial_reason(request, ACTOR, facts)

    # Argument parsing

    def test_parse_valid(self):
        request = parse_copy_to_research_args(copy_args(), ACTOR)
        self.assertEqual(request.origin, ORIGIN)
        self.assertEqual(request.target, RESEARCH_TARGET)
        self.assertEqual(request.receiver, ACTOR)
        self.assertEqual(request.retry_count, 1)

    def test_parse_paths_with_spaces_and_quotes(self):
        # Base64 encoding allows any characters in iRODS paths, except control characters.
        origin = "/tempZone/home/vault-foo/my 'package'"
        request = parse_copy_to_research_args(copy_args(origin=origin, target="/tempZone/home/research-bar/my 'package'"), ACTOR)
        self.assertEqual(request.origin, origin)

    def test_parse_rejects_wrong_number_of_args(self):
        valid = copy_args()
        for a in ["", ACTOR, valid + " extra", valid.replace(" ", "  ", 1), " " + valid, " ".join(valid.split(" ")[:4])]:
            with self.assertRaises(ValueError, msg=a):
                parse_copy_to_research_args(a, ACTOR)

    def test_parse_rejects_other_actor(self):
        with self.assertRaises(ValueError):
            parse_copy_to_research_args(copy_args(actor="mallory#tempZone"), ACTOR)

    def test_parse_rejects_invalid_base64(self):
        valid = copy_args().split(" ")
        for bad in ["not base64!", "YWJj=", "'YWJj'", b64("x")[:-1]]:
            with self.assertRaises(ValueError, msg=bad):
                parse_copy_to_research_args(" ".join([valid[0], bad] + valid[2:]), ACTOR)

    def test_parse_rejects_control_characters(self):
        for origin in [ORIGIN + "\n", ORIGIN + "\x00x", ORIGIN + "\tx"]:
            with self.assertRaises(ValueError, msg=repr(origin)):
                parse_copy_to_research_args(copy_args(origin=origin), ACTOR)
        with self.assertRaises(ValueError):
            parse_copy_to_research_args(copy_args(receiver=ACTOR + "\n"), ACTOR)

    def test_parse_rejects_invalid_retry_count(self):
        for retry in ["", "-1", "1.0", "one", " 1"]:
            with self.assertRaises(ValueError, msg=retry):
                parse_copy_to_research_args(copy_args(retry=retry), ACTOR)

    def test_parse_rejects_invalid_paths(self):
        cases = [
            ("tempZone/home/vault-foo/package", RESEARCH_TARGET),                    # relative origin
            ("/tempZone/home/research-bar/package", RESEARCH_TARGET),                # origin not in vault
            (ORIGIN, "/tempZone/home/vault-bar/package[1700000000]"),               # target in vault
            (ORIGIN, "/tempZone/home/datamanager-cat/package[1700000000]"),         # target in datamanager space
            (ORIGIN, "/tempZone/home/rods/package[1700000000]"),                    # target outside groups
            ("/tempZone/home/vault-foo/../vault-other/package", RESEARCH_TARGET),    # parent reference
            (ORIGIN, "/tempZone/home/research-bar/../research-other/package[1700000000]"),
            ("/tempZone/home/vault-foo//package", RESEARCH_TARGET),                  # empty component
            ("/tempZone/home/vault-foo/./package", RESEARCH_TARGET),                 # '.' component
            (ORIGIN + "/", RESEARCH_TARGET),                                         # trailing slash
            (ORIGIN, RESEARCH_TARGET + "/"),
        ]
        for origin, target in cases:
            with self.assertRaises(ValueError, msg=(origin, target)):
                parse_copy_to_research_args(copy_args(origin=origin, target=target), ACTOR)

    # Checks shared by research and deposit targets

    def test_allowed_research_and_deposit(self):
        self.assertIsNone(self.reason(RESEARCH_FACTS))
        self.assertIsNone(self.reason(DEPOSIT_FACTS, target=DEPOSIT_TARGET))
        self.assertIsNone(self.reason(replace(RESEARCH_FACTS, target_group_role="manager")))

    def test_allowed_folder_within_package(self):
        # The vault browser allows copying the folder that the user is looking at.
        self.assertIsNone(self.reason(RESEARCH_FACTS, origin=ORIGIN + "/original",
                                      target="/tempZone/home/research-bar/original"))

    def test_origin_vault_group_root_denied(self):
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, origin="/tempZone/home/vault-foo",
                                         target="/tempZone/home/research-bar/vault-foo"))

    def test_other_zone_denied(self):
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, origin="/otherZone/home/vault-foo/package[1700000000]"))
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, target="/otherZone/home/research-bar/package[1700000000]"))

    def test_retry_by_user_denied(self):
        # Retries are scheduled by rodsadmin, which skips this policy.
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, retry="2"))
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, retry="0"))

    def test_other_receiver_denied(self):
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, receiver="mallory#tempZone"))
        self.assertIsNotNone(self.reason(DEPOSIT_FACTS, target=DEPOSIT_TARGET, receiver="mallory#tempZone"))

    def test_origin_access(self):
        no_access = replace(RESEARCH_FACTS, origin_readable=False)
        self.assertIsNotNone(self.reason(no_access))
        self.assertIsNotNone(self.reason(replace(DEPOSIT_FACTS, origin_readable=False), target=DEPOSIT_TARGET))
        # Data managers of the origin's category may copy without direct access.
        self.assertIsNone(self.reason(replace(no_access, actor_is_origin_datamanager=True)))

    def test_target_role(self):
        for role in ["reader", "none", ""]:
            self.assertIsNotNone(self.reason(replace(RESEARCH_FACTS, target_group_role=role)), msg=role)
            self.assertIsNotNone(self.reason(replace(DEPOSIT_FACTS, target_group_role=role), target=DEPOSIT_TARGET), msg=role)

    # api_vault_copy_to_research

    def test_research_target_must_be_named_after_origin(self):
        self.assertIsNotNone(self.reason(RESEARCH_FACTS, target="/tempZone/home/research-bar/folder/other"))

    def test_research_target_parent_must_exist(self):
        self.assertIsNotNone(self.reason(replace(RESEARCH_FACTS, target_parent_exists=False)))

    def test_research_target_must_not_exist(self):
        self.assertIsNotNone(self.reason(replace(RESEARCH_FACTS, target_exists=True)))

    def test_research_target_parent_locked(self):
        self.assertIsNotNone(self.reason(replace(RESEARCH_FACTS, target_parent_locked=True)))

    def test_research_target_in_group_root(self):
        self.assertIsNone(self.reason(RESEARCH_FACTS, target="/tempZone/home/research-bar/package[1700000000]"))

    # api_deposit_copy_data_package

    def test_deposit_target_must_exist(self):
        self.assertIsNotNone(self.reason(replace(DEPOSIT_FACTS, target_exists=False), target=DEPOSIT_TARGET))

    def test_deposit_target_must_be_empty(self):
        self.assertIsNotNone(self.reason(replace(DEPOSIT_FACTS, target_has_data=True), target=DEPOSIT_TARGET))

    def test_deposit_target_locked(self):
        self.assertIsNotNone(self.reason(replace(DEPOSIT_FACTS, target_locked=True), target=DEPOSIT_TARGET))

    def test_deposit_target_must_be_deposit_collection(self):
        self.assertIsNotNone(self.reason(DEPOSIT_FACTS, target="/tempZone/home/deposit-pilot"))
        self.assertIsNotNone(self.reason(DEPOSIT_FACTS, target=DEPOSIT_TARGET + "/sub"))
