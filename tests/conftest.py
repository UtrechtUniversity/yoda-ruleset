#!/usr/bin/env python3
"""Yoda API tests.

Usage:
pytest --url <url>
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import requests
import urllib3


def pytest_addoption(parser):
    parser.addoption("--url", action="store", default="https://portal.yoda.test/")
    parser.addoption("--user", action="store", default="functionaladminpriv")
    parser.addoption("--password", action="store", default="test")


def pytest_configure(config):
    global _URL
    _URL = config.getoption("--url")

    global _USER
    _USER = config.getoption("--user")

    global _PASSWORD
    _PASSWORD = config.getoption("--password")

    global _API
    _API = _URL + "api"

    global _CSRF
    global _SESSION
    _CSRF, _SESSION = login(_USER, _PASSWORD)


def api():
    return _API


def csrf():
    return _CSRF


def session():
    return _SESSION


def login(user, password):
    """Login portal and retrieve CSRF and session cookies."""
    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = _URL + 'user/login'
    client = requests.session()

    # Retrieve the CSRF token first
    csrf = client.get(url, verify=False).cookies['csrf_yoda']

    # Login
    login_data = dict(csrf_yoda=csrf, username='functionaladminpriv', password='test', next='/home')
    client.post(url, data=login_data, headers=dict(Referer=url), verify=False)
    client.close()

    # Return CSRF and session cookies.
    return client.cookies['csrf_yoda'], client.cookies['yoda_session']


def api_request(request, data):
    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = api() + "/" + request
    files = {'csrf_yoda': (None, csrf()), 'data': (None, json.dumps(data))}
    cookies = {'csrf_yoda': csrf(), 'yoda_session': session()}

    response = requests.post(url, files=files, cookies=cookies, verify=False)

    # Remove debug info from response body.
    body = response.json()
    if "debug_info" in body:
        del body["debug_info"]

    return (response.status_code, body)
