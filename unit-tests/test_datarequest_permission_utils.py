"""Unit tests for the data request temporary permission policy logic"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase

sys.path.append('..')

from datarequest_permission_utils import parse_temp_permission_args, temp_permission_denial_reason  # noqa: E402

ACTOR = "alice#tempZone"
COLL = "/tempZone/home/datarequests-research/42"


def args(path=COLL, permission="grant", target=ACTOR, actor=ACTOR):
    return f"{actor} {path} {permission} {target}"


class DatarequestPermissionUtilsTest(TestCase):

    def check(self, args_str, roles, status, target_is_dac_member=False, target_is_owner=False):
        """Return the denial reason (None if allowed) for an argument string."""
        request = parse_temp_permission_args(args_str, ACTOR)
        return temp_permission_denial_reason(request, roles, status, target_is_dac_member, target_is_owner)

    def assertAllowed(self, *a, **kw):
        self.assertIsNone(self.check(*a, **kw))

    def assertDenied(self, *a, **kw):
        self.assertIsNotNone(self.check(*a, **kw))

    # Argument parsing

    def test_parse_valid(self):
        request = parse_temp_permission_args(args(path=COLL + "/dta", permission="revoke"), ACTOR)
        self.assertEqual(request.zone, "tempZone")
        self.assertEqual(request.request_id, "42")
        self.assertEqual(request.subpath, "dta")
        self.assertEqual(request.permission, "revoke")
        self.assertEqual(request.target, ACTOR)
        self.assertEqual(request.target_name, "alice")
        self.assertTrue(request.is_self)

    def test_parse_collection_has_no_subpath(self):
        self.assertIsNone(parse_temp_permission_args(args(), ACTOR).subpath)

    def test_parse_other_target(self):
        request = parse_temp_permission_args(args(path=COLL + "/datarequest.json", permission="grantread",
                                                  target="bob@example.org#tempZone"), ACTOR)
        self.assertFalse(request.is_self)
        self.assertEqual(request.target_name, "bob@example.org")

    def test_parse_rejects_wrong_number_of_args(self):
        for a in ["", ACTOR, f"{ACTOR} {COLL} grant", args() + " extra", args().replace(" ", "  ", 1), " " + args()]:
            with self.assertRaises(ValueError, msg=a):
                parse_temp_permission_args(a, ACTOR)

    def test_parse_rejects_unsafe_characters(self):
        # Quotes and backslashes change how msiExecCmd splits arguments, and could
        # break out of the string literals that the script passes to irule.
        for path in [COLL + "/a'b", COLL + '/a"b', COLL + "/a\\b", COLL + "/a\tb", COLL + "/a\nb", COLL + "/a\x00b"]:
            with self.assertRaises(ValueError, msg=repr(path)):
                parse_temp_permission_args(args(path=path), ACTOR)

    def test_parse_rejects_quoted_argument_hiding_extra_args(self):
        # msiExecCmd would treat the quoted part as one argument, so a naive split
        # would see different arguments than the script.
        with self.assertRaises(ValueError):
            parse_temp_permission_args(f"{ACTOR} '{COLL} own' grant {ACTOR}", ACTOR)

    def test_parse_rejects_other_actor(self):
        with self.assertRaises(ValueError):
            parse_temp_permission_args(args(actor="borg#tempZone"), ACTOR)

    def test_parse_rejects_unused_permissions(self):
        for permission in ["own", "write", "null", "admin:own", "GRANT", ""]:
            with self.assertRaises(ValueError, msg=permission):
                parse_temp_permission_args(f"{ACTOR} {COLL} {permission} {ACTOR}", ACTOR)

    def test_parse_rejects_paths_outside_datarequest_collection(self):
        for path in ["/tempZone/home",
                     "/tempZone/home/research-foo",
                     "/tempZone/home/rods",
                     "/tempZone/home/datarequests-research",
                     "/tempZone/home/datarequests-research/",
                     "/tempZone/home/datarequests-research/42/",
                     "/tempZone/home/datarequests-research/abc",
                     "/tempZone/home/datarequests-researchers/42",
                     "/tempZone/home/datarequests-research/42/../../research-foo",
                     "/tempZone/home/datarequests-research/42/./dta",
                     "/tempZone/home/datarequests-research/42//dta",
                     "tempZone/home/datarequests-research/42",
                     "/tempZone/home/vault-foo",
                     "/tempZone/home/vault-foo/home/datarequests-research/42",
                     "/tempZone/home/vault-foo/../research-foo"]:
            with self.assertRaises(ValueError, msg=path):
                parse_temp_permission_args(args(path=path), ACTOR)

    def test_parse_rejects_other_zones(self):
        with self.assertRaises(ValueError):
            parse_temp_permission_args(args(path="/otherZone/home/datarequests-research/42"), ACTOR)
        with self.assertRaises(ValueError):
            parse_temp_permission_args(args(path=COLL + "/datarequest.json", permission="grantread",
                                            target="bob#otherZone"), ACTOR)

    def test_parse_rejects_invalid_users(self):
        for target in ["bob", "bob#", "#tempZone", "bob#tempZone#x", "bob/x#tempZone"]:
            with self.assertRaises(ValueError, msg=target):
                parse_temp_permission_args(args(target=target), ACTOR)

    # file_write() / file_lock() on the data request collection

    def test_request_collection_allowed_cases(self):
        cases = [
            (["PM"], "SUBMITTED"),             # preliminary review
            (["DM"], "PRELIMINARY_ACCEPT"),    # data manager review
            (["PM"], "DATAMANAGER_ACCEPT"),    # assignment
            (["PM"], "DATAMANAGER_REJECT"),    # assignment + feedback
            (["PM"], "DATAMANAGER_RESUBMIT"),  # assignment + feedback
            (["REV"], "UNDER_REVIEW"),         # review
            (["PM"], "REVIEWED"),              # evaluation
            (["PM"], "DAO_SUBMITTED"),         # evaluation
            (["OWN"], "APPROVED"),             # preregistration
        ]
        for roles, status in cases:
            for permission in ["grant", "revoke"]:
                self.assertIsNone(self.check(args(permission=permission), roles, status), msg=(roles, status, permission))

    def test_request_collection_wrong_role_or_status(self):
        cases = [
            (["DM"], "SUBMITTED"),
            (["PM"], "PRELIMINARY_ACCEPT"),
            (["DAC"], "UNDER_REVIEW"),         # DAC member that is not assigned as reviewer
            (["REV"], "REVIEWED"),
            (["OWN"], "SUBMITTED"),
            (["OWN"], "DTA_READY"),
            (["PM", "DM", "DAC"], "PREREGISTRATION_SUBMITTED"),
            ([], "APPROVED"),
        ]
        for roles, status in cases:
            self.assertIsNotNone(self.check(args(), roles, status), msg=(roles, status))

    def test_request_collection_read_only_for_owner(self):
        # file_lock() downgrades the temporary write access of the owner to read.
        self.assertAllowed(args(permission="read"), ["OWN"], "APPROVED")
        self.assertDenied(args(permission="read"), ["PM"], "SUBMITTED")

    def test_request_collection_no_grantread(self):
        self.assertDenied(args(permission="grantread"), ["OWN"], "APPROVED")

    def test_request_collection_not_for_other_users(self):
        self.assertDenied(args(target="bob#tempZone"), ["PM"], "SUBMITTED", target_is_dac_member=True)

    # api_datarequest_attachment_upload_permission

    def test_attachments(self):
        path = COLL + "/attachments"
        self.assertAllowed(args(path=path, permission="grant"), ["OWN"], "PENDING_ATTACHMENTS")
        self.assertAllowed(args(path=path, permission="grantread"), ["OWN"], "PENDING_ATTACHMENTS")
        self.assertDenied(args(path=path, permission="revoke"), ["OWN"], "PENDING_ATTACHMENTS")
        self.assertDenied(args(path=path, permission="grant"), ["OWN"], "SUBMITTED")
        self.assertDenied(args(path=path, permission="grant"), ["PM", "DM"], "PENDING_ATTACHMENTS")
        self.assertDenied(args(path=path, permission="grant", target="bob#tempZone"), ["OWN"], "PENDING_ATTACHMENTS")

    # api_datarequest_dta_upload_permission

    def test_dta(self):
        path = COLL + "/dta"
        for status in ["PREREGISTRATION_CONFIRMED", "DAO_APPROVED", "DTA_READY"]:
            for permission in ["grant", "revoke"]:
                self.assertIsNone(self.check(args(path=path, permission=permission), ["DM"], status), msg=(status, permission))
        self.assertDenied(args(path=path, permission="grantread"), ["DM"], "DTA_READY")
        self.assertDenied(args(path=path, permission="grant"), ["DM"], "APPROVED")
        self.assertDenied(args(path=path, permission="grant"), ["OWN", "PM"], "DTA_READY")

    # api_datarequest_signed_dta_upload_permission

    def test_signed_dta(self):
        path = COLL + "/signed_dta"
        for status in ["DTA_READY", "DTA_SIGNED"]:
            for permission in ["grant", "grantread"]:
                self.assertIsNone(self.check(args(path=path, permission=permission), ["OWN"], status), msg=(status, permission))
        self.assertDenied(args(path=path, permission="revoke"), ["OWN"], "DTA_READY")
        self.assertDenied(args(path=path, permission="grant"), ["OWN"], "PREREGISTRATION_CONFIRMED")
        self.assertDenied(args(path=path, permission="grant"), ["DM"], "DTA_READY")

    # assign_request()

    def test_assign_reviewers(self):
        target = "bob#tempZone"
        for name in ["datarequest.json", "preliminary_review.json", "datamanager_review.json", "attachments/file.pdf"]:
            for status in ["DATAMANAGER_ACCEPT", "DATAMANAGER_REJECT", "DATAMANAGER_RESUBMIT"]:
                a = args(path=f"{COLL}/{name}", permission="grantread", target=target)
                self.assertIsNone(self.check(a, ["PM"], status, target_is_dac_member=True), msg=(name, status))

    def test_assign_reviewers_project_manager_is_also_dac_member(self):
        self.assertAllowed(args(path=COLL + "/datarequest.json", permission="grantread"),
                           ["PM", "DAC"], "DATAMANAGER_ACCEPT", target_is_dac_member=True)

    def test_assign_reviewers_denied(self):
        target = "bob#tempZone"
        path = COLL + "/datarequest.json"
        ok = {"roles": ["PM"], "status": "DATAMANAGER_ACCEPT", "target_is_dac_member": True}

        # Sanity check of the baseline.
        self.assertAllowed(args(path=path, permission="grantread", target=target), **ok)

        self.assertDenied(args(path=path, permission="grant", target=target), **ok)
        self.assertDenied(args(path=path, permission="revoke", target=target), **ok)
        self.assertDenied(args(path=path, permission="grantread", target=target), **{**ok, "roles": ["DM", "DAC", "OWN"]})
        self.assertDenied(args(path=path, permission="grantread", target=target), **{**ok, "status": "UNDER_REVIEW"})
        self.assertDenied(args(path=path, permission="grantread", target=target), **{**ok, "target_is_dac_member": False})
        self.assertDenied(args(path=path, permission="grantread", target=target), **ok, target_is_owner=True)
        self.assertDenied(args(path=path, permission="grantread", target="rods#tempZone"), **ok)

    def test_assign_reviewers_only_review_documents(self):
        ok = {"roles": ["PM"], "status": "DATAMANAGER_ACCEPT", "target_is_dac_member": True}
        for name in ["review_carol.json", "evaluation.json", "feedback.json", "attachments", "attachments/a/b",
                     "dta/dta.pdf", "signed_dta", "datarequest.json/x"]:
            self.assertIsNotNone(self.check(args(path=f"{COLL}/{name}", permission="grantread", target="bob#tempZone"), **ok),
                                 msg=name)

    # Other paths

    def test_unknown_subpaths_denied(self):
        for name in ["provenance", "datarequest.json.bak", "dta2", "attachments2"]:
            self.assertDenied(args(path=f"{COLL}/{name}"), ["PM", "DM", "OWN", "REV"], "SUBMITTED")
