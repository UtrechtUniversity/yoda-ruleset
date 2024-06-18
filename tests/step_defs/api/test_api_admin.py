# coding=utf-8
"""Admin access check API feature tests."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'
from pytest_bdd import (
    given,
    then,
    parsers,
    scenarios,
)

from conftest import api_request

scenarios('../../features/api/api_admin.feature')


@given(parsers.parse("the admin has access API is queried"), target_fixture="api_response") #TODO: Need the group name arg?
def api_admin_has_access(user):

    api_response = api_request(
        user, 
        "admin_has_access",
        {}
    )
    print(api_response)#remove
    return api_response

@then(parsers.parse('the response result is "{expected_result:w}"'))
def api_response_data(api_response, expected_result):
    """
    Checks if the API response matches the expected boolean result.
    """
    # Convert the expected result to a boolean
    expected_bool = expected_result.lower() == 'true'
    
    # Extract HTTP status and response data
    _, response_data = api_response
    
    # Assert the actual result matches the expected boolean value
    assert response_data['data'] == expected_bool, f"Expected {expected_bool}, got {response_data['data']}"
