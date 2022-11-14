# coding=utf-8
"""Research API feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from io import BytesIO
import json
import os
from collections import OrderedDict

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when
)

from conftest import api_request, upload_data

scenarios('../../features/api/api_schema_transformation.feature')


@given(parsers.parse("a metadata file with schema <schema_from> is uploaded to folder with schema <schema_to>"), target_fixture="api_response")
def ui_transform_metadata_json_upload_on_access(user, schema_from, schema_to):
    cwd = os.getcwd()
	
    with open("{}\\files\\transformations\\{} to {}\\yoda-metadata.json".format(cwd, schema_from, schema_to)) as f:
        metadata = f.read()

    return upload_data(
        user,
        "yoda-metadata.json",
        "/research-{}".format(schema_to),
        metadata
    )


@given(parsers.parse("transformation of metadata is successful for collection <schema_to>"), target_fixture="api_response")
def api_transform_metadata(user, schema_to):
    collection = '/tempZone/home/research-{}'.format(schema_to)
    return api_request(
        user,
        "transform_metadata",
        {"coll": collection}
    )
