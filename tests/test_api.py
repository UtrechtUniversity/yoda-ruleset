#!/usr/bin/env python3
"""Yoda API tests.

Usage:
pytest --api <url> --csrf <csrf> --session <session> -v
"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from conftest import api_request


def test_research_file_rename():
    http_status, body = api_request(
        "research_file_rename",
        {"new_file_name": "yoda-metadata-renamed.json",
         "coll": "/tempZone/home/research-initial1",
         "org_file_name": "yoda-metadata.json"}
    )

    assert http_status == 200
    assert body == {"status": "ok", "status_info": None, "data": {"proc_status_info": "", "proc_status": "ok"}}


def test_research_file_delete():
    http_status, body = api_request(
        "research_file_delete",
        {"coll": "/tempZone/home/research-initial1",
         "file_name": "yoda-metadata-renamed.json"}
    )

    assert http_status == 200
    assert body == {"status": "ok", "status_info": None, "data": {"proc_status_info": "", "proc_status": "ok"}}
