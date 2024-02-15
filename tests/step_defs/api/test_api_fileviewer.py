# coding=utf-8
"""Browse API feature tests."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
)

from conftest import api_request

scenarios('../../features/api/api_fileviewer.feature')


@given(parsers.parse("the Yoda text file view API is queried with {file}"), target_fixture="api_response")
def api_load_text_obj(user, file):
    return api_request(
        user,
        "load_text_obj",
        {"file_path": file}
    )
