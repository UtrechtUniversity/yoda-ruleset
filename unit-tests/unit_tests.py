__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from unittest import makeSuite, TestSuite

from test_group_import import GroupImportTest
from test_json_datacite import JsonDataciteAffiliationsListTest, JsonDataciteContactPersonTest, JsonDataciteContributorTest, JsonDataciteCreatorTest
from test_metadata_utils import MetadataUtilsTest
from test_policies import PoliciesTest
from test_publication_utils import PublicationUtilsTest
from test_revisions import RevisionTest
from test_schema_transformations import CorrectifyIsniTest, CorrectifyOrcidTest, CorrectifyResearcherIDTest, CorrectifyScopusTest, MergeGeoKeywordsTest, RenameRelatedDatapackageTest
from test_util_api import UtilAPITest
from test_util_config import UtilConfigTest
from test_util_misc import UtilMiscTest
from test_util_pathutil import UtilPathutilTest
from test_util_schema_utils import SchemaUtilsTest
from test_util_yoda_names import UtilYodaNamesTest
from test_vault import VaultTest


def suite():
    test_suite = TestSuite()
    test_suite.addTest(makeSuite(CorrectifyIsniTest))
    test_suite.addTest(makeSuite(CorrectifyOrcidTest))
    test_suite.addTest(makeSuite(CorrectifyScopusTest))
    test_suite.addTest(makeSuite(CorrectifyResearcherIDTest))
    test_suite.addTest(makeSuite(MergeGeoKeywordsTest))
    test_suite.addTest(makeSuite(RenameRelatedDatapackageTest))
    test_suite.addTest(makeSuite(GroupImportTest))
    test_suite.addTest(makeSuite(JsonDataciteAffiliationsListTest))
    test_suite.addTest(makeSuite(JsonDataciteContactPersonTest))
    test_suite.addTest(makeSuite(JsonDataciteContributorTest))
    test_suite.addTest(makeSuite(JsonDataciteCreatorTest))
    test_suite.addTest(makeSuite(MetadataUtilsTest))
    test_suite.addTest(makeSuite(PoliciesTest))
    test_suite.addTest(makeSuite(PublicationUtilsTest))
    test_suite.addTest(makeSuite(RevisionTest))
    test_suite.addTest(makeSuite(SchemaUtilsTest))
    test_suite.addTest(makeSuite(UtilAPITest))
    test_suite.addTest(makeSuite(UtilConfigTest))
    test_suite.addTest(makeSuite(UtilMiscTest))
    test_suite.addTest(makeSuite(UtilPathutilTest))
    test_suite.addTest(makeSuite(UtilYodaNamesTest))
    test_suite.addTest(makeSuite(VaultTest))
    return test_suite
