"""Unit tests for the policies"""

__copyright__ = 'Copyright (c) 2023-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

sys.path.append('..')

# The 'user' module (imported by policies_utils) depends on iRODS-provided
# modules that are not available when running the unit tests. Stub them out
# before importing policies_utils so it can be imported here.
for _irods_module in ('genquery', 'session_vars', 'irods_types'):
    sys.modules.setdefault(_irods_module, MagicMock())

from policies_utils import _is_safe_genquery_inp, check_anonymous_access_allowed, check_max_connections_exceeded, format_client_description, should_resource_be_replication_exempt, should_resource_trigger_policies, should_transition_submitted_to_accepted_immediately  # noqa: E402
from util import config  # noqa: E402


resc_config = config.Config(resource_primary=["irodsResc"],
                            resource_vault=["irodsResc"],
                            resource_replica=["irodsRescRepl"],
                            resource_trigger_pol=["triggerResc"],
                            resource_repl_exempt=["exemptResc"])


class PoliciesTest(TestCase):

    def test_is_safe_genquery_inp(self):
        # Queries that do not pose any problems
        # select D_DATA_ID where DATA_NAME = 'rods' and COLL_NAME = '/tempZone/home'
        selectInp = {401: 1}
        sqlCondInp = [403, 501]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select D_CREATE_TIME, D_MODIFY_TIME, DATA_MODE, D_RESC_ID, D_DATA_ID, DATA_SIZE, D_OWNER_NAME, D_OWNER_ZONE, D_REPL_STATUS, D_DATA_CHECKSUM where COLL_NAME ='/tempZone/home' and DATA_NAME ='rods'
        selectInp = {419: 1, 420: 1, 421: 1, 423: 1, 401: 1, 407: 1, 411: 1, 412: 1, 413: 1, 415: 1}
        sqlCondInp = [501, 403]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select COLL_INFO2, COLL_ID, COLL_NAME, COLL_OWNER_NAME, COLL_OWNER_ZONE, COLL_CREATE_TIME, COLL_MODIFY_TIME, COLL_TYPE, COLL_INFO1 where COLL_NAME ='/tempZone/home/rods'
        selectInp = {512: 1, 500: 1, 501: 1, 503: 1, 504: 1, 508: 1, 509: 1, 510: 1, 511: 1}
        sqlCondInp = [501]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select D_CREATE_TIME, D_MODIFY_TIME, DATA_MODE, D_DATA_ID, DATA_NAME, COLL_NAME, DATA_SIZE where COLL_NAME  = '/tempZone/home/rods'
        selectInp = {419: 1, 420: 1, 421: 1, 401: 1, 403: 1, 501: 1, 407: 1}
        sqlCondInp = [501]
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select ZONE_CONNECTION, ZONE_COMMENT, ZONE_NAME, ZONE_TYPE where
        selectInp = {104: 1, 105: 1, 102: 1, 103: 1}
        sqlCondInp = []
        self.assertTrue(_is_safe_genquery_inp(selectInp, sqlCondInp))

        # select META_COLL_ATTR_VALUE where COLL_NAME = '/a/b/c'
        selectInp = {611: 1}
        sqlCondInp = [501]
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
        sqlCondInp = [403]
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

    def test_should_transition_submitted_to_accepted_immediately(self):
        self.assertTrue(should_transition_submitted_to_accepted_immediately("/tempZone/home/research-foo/datapackage", []))
        self.assertFalse(should_transition_submitted_to_accepted_immediately("/tempZone/home/research-foo/datapackage", [("datamanager", "tempZone")]))
        self.assertTrue(should_transition_submitted_to_accepted_immediately("/tempZone/home/deposit-foo/datapackage", []))
        self.assertTrue(should_transition_submitted_to_accepted_immediately("/tempZone/home/deposit-foo/datapackage", [("any", "any")]))
        self.assertFalse(should_transition_submitted_to_accepted_immediately("/tempZone/home/not-deposit-or-research/datapackage", []))
        self.assertFalse(should_transition_submitted_to_accepted_immediately("/tempZone/home/not-deposit-or-research/datapackage", [("any", "any")]))

    def test_should_resource_trigger_policies(self):
        self.assertTrue(should_resource_trigger_policies(resc_config, "irodsResc"))
        self.assertTrue(should_resource_trigger_policies(resc_config, "triggerResc"))
        self.assertFalse(should_resource_trigger_policies(resc_config, "exemptResc"))
        self.assertFalse(should_resource_trigger_policies(resc_config, "randomResc"))

    def test_should_resource_be_replication_exempt(self):
        self.assertFalse(should_resource_be_replication_exempt(resc_config, "irodsResc"))
        self.assertFalse(should_resource_be_replication_exempt(resc_config, "triggerResc"))
        self.assertTrue(should_resource_be_replication_exempt(resc_config, "exemptResc"))
        self.assertFalse(should_resource_be_replication_exempt(resc_config, "randomResc"))

    def test_format_client_description(self):
        self.assertEqual(format_client_description("foo"), "client: foo")
        # Strip trailing semicolons
        self.assertEqual(format_client_description("foo;"), "client: foo")
        # Filter client name if it has weird characters like newlines
        self.assertEqual(format_client_description("foo\nbar"), "client: <filtered>")

    @patch("policies_utils.config")
    def test_check_anonymous_access_allowed(self, mock_config):
        # ctx is not used by the function, so a dummy value suffices.
        ctx = MagicMock()

        # Localhost is always allowed, even when no remote addresses are configured.
        mock_config.remote_anonymous_access = []
        self.assertTrue(check_anonymous_access_allowed(ctx, "127.0.0.1"))

        # A non-local address is only allowed when it is in the configured permit list.
        mock_config.remote_anonymous_access = ["1.2.3.4", "1.2.3.5"]
        self.assertTrue(check_anonymous_access_allowed(ctx, "1.2.3.4"))
        self.assertTrue(check_anonymous_access_allowed(ctx, "1.2.3.5"))
        # Localhost remains allowed alongside configured remote addresses.
        self.assertTrue(check_anonymous_access_allowed(ctx, "127.0.0.1"))
        # Addresses not in the permit list are rejected.
        self.assertFalse(check_anonymous_access_allowed(ctx, "1.2.3.6"))
        self.assertFalse(check_anonymous_access_allowed(ctx, "8.8.8.8"))

    @patch("policies_utils.user")
    @patch("policies_utils.config")
    def test_check_max_connections_exceeded(self, mock_config, mock_user):
        ctx = MagicMock()

        # When the check is disabled, the number of connections is never exceeded,
        # regardless of the observed number of connections.
        mock_config.user_max_connections_enabled = False
        mock_config.user_max_connections_number = 4
        mock_user.name.return_value = "researcher"
        mock_user.number_of_connections.return_value = 100
        self.assertFalse(check_max_connections_exceeded(ctx))

        # The check does not apply to the 'anonymous' and 'rods' users.
        mock_config.user_max_connections_enabled = True
        mock_user.number_of_connections.return_value = 100
        for exempt_user in ("anonymous", "rods"):
            mock_user.name.return_value = exempt_user
            self.assertFalse(check_max_connections_exceeded(ctx))

        # For a regular user, the limit is exceeded only when the observed number
        # of connections is strictly greater than the configured maximum.
        mock_user.name.return_value = "researcher"
        mock_user.number_of_connections.return_value = 5
        self.assertTrue(check_max_connections_exceeded(ctx))

        # The configured maximum itself is still allowed (boundary case).
        mock_user.number_of_connections.return_value = 4
        self.assertFalse(check_max_connections_exceeded(ctx))

        mock_user.number_of_connections.return_value = 3
        self.assertFalse(check_max_connections_exceeded(ctx))
