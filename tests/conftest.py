#!/usr/bin/env python3
"""Yoda tests configuration."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import re

import pytest
import requests
import urllib3
from pytest_bdd import (
    given,
    parsers,
    then,
    when,
)


portal_url = "https://portal.yoda.test"
api_url = "https://portal.yoda.test/api"
password = "test"
users = ['researcher',
         'datamanager',
         'groupmanager',
         'technicaladmin']
user_cookies = {}

datarequest = False
deposit = False
intake = False
login_oidc = False


def pytest_addoption(parser):
    parser.addoption("--url", action="store", default="https://portal.yoda.test")
    parser.addoption("--password", action="store", default="test")
    parser.addoption("--datarequest", action="store_true", default=False, help="Run datarequest tests")
    parser.addoption("--deposit", action="store_true", default=False, help="Run deposit tests")
    parser.addoption("--intake", action="store_true", default=False, help="Run intake tests")
    parser.addoption("--oidc", action="store_true", default=False, help="Run login OIDC tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "datarequest: Run datarequest tests")
    config.addinivalue_line("markers", "deposit: Run deposit tests")
    config.addinivalue_line("markers", "intake: Run intake tests")

    global portal_url
    portal_url = config.getoption("--url")

    global api_url
    api_url = "{}/api".format(portal_url)

    global password
    password = config.getoption("--password")

    global datarequest
    datarequest = config.getoption("--datarequest")

    global deposit
    deposit = config.getoption("--deposit")

    global intake
    intake = config.getoption("--intake")

    global login_oidc
    login_oidc = config.getoption("--oidc")

    global users
    if datarequest:
        users = users + ['projectmanager', 'dmcmember']

    # Store cookies for each user.
    for user in users:
        csrf, session = login(user, password)
        user_cookies[user] = (csrf, session)


def pytest_bdd_apply_tag(tag, function):
    if tag == 'datarequest' and not datarequest:
        marker = pytest.mark.skip(reason="Skip datarequest")
        marker(function)
        return True
    elif tag == 'deposit' and not deposit:
        marker = pytest.mark.skip(reason="Skip deposit")
        marker(function)
        return True
    elif tag == 'intake' and not intake:
        marker = pytest.mark.skip(reason="Skip intake")
        marker(function)
        return True
    elif tag == 'oidc' and not login_oidc:
        marker = pytest.mark.skip(reason="Skip login OIDC")
        marker(function)
        return True
    else:
        # Fall back to pytest-bdd's default behavior
        return None


def login(user, password):
    """Login portal and retrieve CSRF and session cookies."""
    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = "{}/user/login".format(portal_url)

    client = requests.session()

    # Retrieve the login CSRF token.
    content = client.get(url, verify=False).content.decode()
    p = re.compile("tokenValue: '([a-zA-Z0-9._-]*)'")
    csrf = p.findall(content)[0]

    # Login as user.
    login_data = dict(csrf_token=csrf, username=user, password=password, next='/')
    response = client.post(url, data=login_data, headers=dict(Referer=url), verify=False)
    session = client.cookies['session']
    client.close()

    # Retrieve the authenticated CSRF token.
    content = response.content.decode()
    p = re.compile("tokenValue: '([a-zA-Z0-9._-]*)'")
    csrf = p.findall(content)[0]

    # Return CSRF and session cookies.
    return csrf, session


def api_request(user, request, data, timeout=10):
    # Retrieve user cookies.
    csrf, session = user_cookies[user]

    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Make API request.
    url = api_url + "/" + request
    files = {'csrf_token': (None, csrf), 'data': (None, json.dumps(data))}
    cookies = {'session': session}
    headers = {'referer': 'https://portal.yoda.test/'}
    response = requests.post(url, headers=headers, files=files, cookies=cookies, verify=False, timeout=timeout)

    # Remove debug info from response body.
    body = response.json()
    if "debug_info" in body:
        del body["debug_info"]

    return (response.status_code, body)


def upload_data(user, file, folder):
    # Retrieve user cookies.
    csrf, session = user_cookies[user]

    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Make POST request.
    url = portal_url + "/research/upload"

    files = {"csrf_token": (None, csrf),
             "filepath": (None, folder),
             "flowChunkNumber": (None, "1"),
             "flowChunkSize": (None, "10485760"),
             "flowCurrentChunkSize": (None, "4"),
             "flowTotalSize": (None, "4"),
             "flowIdentifier": (None, "4-{}".format(file)),
             "flowFilename": (None, file),
             "flowRelativePath": (None, file),
             "flowTotalChunks": (None, "1"),
             "file": (file, "test")}

    cookies = {'session': session}
    headers = {'referer': 'https://portal.yoda.test/'}
    response = requests.post(url, headers=headers, files=files, cookies=cookies, verify=False, timeout=10)

    return (response.status_code, response)


def post_form_data(user, request, files):
    # Retrieve user cookies.
    csrf, session = user_cookies[user]

    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Make POST request.
    url = portal_url + "/" + request
    files['csrf_token'] = (None, csrf)
    cookies = {'session': session}
    headers = {'referer': 'https://portal.yoda.test/'}
    response = requests.post(url, headers=headers, files=files, cookies=cookies, verify=False, timeout=10)

    return (response.status_code, response)


@given('user "<user>" is authenticated', target_fixture="user")
@given(parsers.parse('user "{user}" is authenticated'), target_fixture="user")
def api_user_authenticated(user):
    assert user in users
    return user


@given('user "<user>" is logged in')
@given(parsers.parse('user "{user}" is logged in'))
@when('user "<user>" logs in')
def ui_login(browser, user):
    url = "{}/user/gate".format(portal_url)
    browser.visit(url)

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)
    browser.find_by_id('f-login-submit').click()

    # Fill in password
    browser.find_by_id('f-login-password').fill(password)

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()


@given('user is not logged in')
def ui_logout(browser):
    url = "{}/user/logout".format(portal_url)
    browser.visit(url)


@given(parsers.parse('module "{module}" is shown'))
@when(parsers.parse('module "{module}" is shown'))
@given(parsers.parse('page "{module}" is shown'))
@when(parsers.parse('page "{module}" is shown'))
def ui_module_shown(browser, module):
    url = "{}/{}".format(portal_url, module)
    browser.visit(url)


@given(parsers.parse('text "{text}" is shown'))
@when(parsers.parse('text "{text}" is shown'))
@then(parsers.parse('text "{text}" is shown'))
def ui_text_shown(browser, text):
    assert browser.is_text_present(text)


@then(parsers.parse('the response status code is "{code:d}"'))
def api_response_code(api_response, code):
    http_status, _ = api_response
    assert http_status == code


@given('collection "<collection>" exists')
def collection_exists(user, collection):
    http_status, _ = api_request(
        user,
        "browse_folder",
        {"coll": collection}
    )
    assert http_status == 200


@given('"<collection>" is unlocked')
def collection_is_unlocked(user, collection):
    _, body = api_request(
        user,
        "research_collection_details",
        {"path": collection}
    )

    if body["data"]["status"] == "LOCKED":
        http_status, _ = api_request(
            user,
            "folder_unlock",
            {"coll": collection}
        )
        assert http_status == 200
    else:
        assert body["data"]["status"] == "" or body["data"]["status"] == "SECURED"


@given('"<collection>" is locked')
def collection_is_locked(user, collection):
    _, body = api_request(
        user,
        "research_collection_details",
        {"path": collection}
    )

    if body["data"]["status"] != "LOCKED":
        http_status, _ = api_request(
            user,
            "folder_lock",
            {"coll": collection}
        )
        assert http_status == 200
    else:
        assert body["data"]["status"] == "LOCKED"
