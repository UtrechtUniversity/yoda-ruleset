#!/usr/bin/env python3
"""Yoda tests configuration."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json

import requests
import urllib3
from pytest_bdd import (
    given,
    parsers,
)


portal_url = "https://portal.yoda.test/"
api_url = "https://portal.yoda.test/api"
password = "test"
users = ['researcher',
         'datamanager',
         'technicaladmin',
         'bodmember',
         'dmcmember',
         'groupmanager']
user_cookies = {}


def pytest_addoption(parser):
    parser.addoption("--url", action="store", default="https://portal.yoda.test/")
    parser.addoption("--password", action="store", default="test")


def pytest_configure(config):
    global portal_url
    portal_url = config.getoption("--url")

    global api_url
    api_url = portal_url + "api"

    password = config.getoption("--password")

    # Store cookies for each user.
    for user in users:
        csrf, session = login(user, password)
        user_cookies[user] = (csrf, session)


def login(user, password):
    """Login portal and retrieve CSRF and session cookies."""
    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = portal_url + 'user/login'

    client = requests.session()

    # Retrieve the CSRF token first
    csrf = client.get(url, verify=False).cookies['csrf_yoda']

    # Login as user.
    login_data = dict(csrf_yoda=csrf, username=user, password=password, next='/home')
    client.post(url, data=login_data, headers=dict(Referer=url), verify=False)
    client.close()

    # Return CSRF and session cookies.
    return client.cookies['csrf_yoda'], client.cookies['yoda_session']


def api_request(user, request, data):
    # Retrieve user cookies.
    csrf, session = user_cookies[user]

    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Make API request.
    url = api_url + "/" + request
    files = {'csrf_yoda': (None, csrf), 'data': (None, json.dumps(data))}
    cookies = {'csrf_yoda': csrf, 'yoda_session': session}

    response = requests.post(url, files=files, cookies=cookies, verify=False, timeout=10)

    # Remove debug info from response body.
    body = response.json()
    if "debug_info" in body:
        del body["debug_info"]

    return (response.status_code, body)


def post_form_data(user, request, files):
    # Retrieve user cookies.
    csrf, session = user_cookies[user]

    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Make POST request.
    url = portal_url + "/" + request
    files['csrf_yoda'] = (None, csrf)
    cookies = {'csrf_yoda': csrf, 'yoda_session': session}

    response = requests.post(url, files=files, cookies=cookies, verify=False, timeout=10)

    return (response.status_code, response)


@given('user "<user>" is authenticated', target_fixture="user")
@given(parsers.parse('user "{user}" is authenticated'), target_fixture="user")
def api_user_authenticated(user):
    assert user in users
    return user
