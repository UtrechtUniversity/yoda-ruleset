# coding=utf-8
"""Ping/echo API feature tests.

These tests document how the API framework in util/api.py (de)serializes
various character encodings, end-to-end through the normal API request path
(python-irodsclient, iRODS and back).
"""

__copyright__ = 'Copyright (c) 2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

from conftest import api_request

scenarios('../../features/api/api_ping.feature')

# String payloads echoed back verbatim by api_ping
STRING_PAYLOADS = {
    "empty_string": "",
    "ascii_only_letters": "Hello world",
    "ascii_with_numbers": "The 39 steps",
    "ascii_with_punctuation": "Hello `~!@#$%^&*()-_=+;:'\"\\|<>,.?/",
    "ascii_with_newline": "Line 1\nLine 2",
    "ascii_long_10k": 9000 * "a",
    "non_ascii_letters": "blåbær smör mjólk brauð",
    "control_chars": "tab\there newline\nreturn\rnuli\0bell\a",
    "cjk": "日本語 한국어",  # Kanji and Korean Unicode
    "emoji_astral": "\U0001f600\U0001f389",  # Unicode outside basic multilingual plane (BMP)
}


@when(parsers.parse('the ping API is queried with the "{case}" payload'), target_fixture="api_response")
def ping_query(user, case):
    return api_request(user, "ping", {"x": STRING_PAYLOADS[case]})


@then(parsers.parse('the ping response returns the "{case}" payload unchanged'))
def ping_response_echoes(api_response, case):
    _, body = api_response
    payload = STRING_PAYLOADS[case]

    assert body["status"] == "ok", body
    assert body["data"] == payload


@then(parsers.parse('the ping response is an error named "{name}"'))
def ping_response_error(api_response, name):
    _, body = api_response
    assert body["status"] == "error_" + name, body
