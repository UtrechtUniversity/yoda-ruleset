# coding=utf-8
"""Fileviewer UI feature tests."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

from conftest import portal_url

scenarios('../../features/ui/ui_admin.feature')


@when(parsers.parse('user opens link to admin page'))
def ui_admin_access(browser):
    url = "{}/admin".format(portal_url)
    browser.visit(url)

@then('the text Administration is shown')
def ui_admin_administration_present(browser):
    print("browser HTML", browser.html)
    assert browser.is_text_present('administration')
