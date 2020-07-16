#!/usr/bin/env python3
"""Yoda API tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session> -v
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import requests
import urllib3


def pytest_addoption(parser):
    parser.addoption("--api", action="store", default="https://portal.yoda.test/api")
    parser.addoption("--csrf", action="store", default="36185869eaebe1f3199eb4ae6824e5bc")
    parser.addoption("--session", action="store", default="pjpr2qp8h5452ftisi49ibfccb8q5rt7")


def pytest_configure(config):
    global _API
    _API = config.getoption("--api")

    global _CSRF
    _CSRF = config.getoption("--csrf")

    global _SESSION
    _SESSION = config.getoption("--session")


def api():
    return _API


def csrf():
    return _CSRF


def session():
    return _SESSION


def api_request(request, data):
    # Disable unsecure connection warning.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = api() + "/" + request
    files = {'csrf_yoda': (None, csrf()), 'data': (None, json.dumps(data))}
    cookies = {'csrf_yoda': csrf(), 'yoda_session': session()}

    response = requests.post(url, files=files, cookies=cookies, verify=False)

    # Remove debug info from response body.
    body = response.json()
    del body["debug_info"]

    return (response.status_code, body)
