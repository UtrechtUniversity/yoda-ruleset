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

scenarios('../../features/ui/ui_fileviewer.feature')


@when(parsers.parse('user opens link to fileviewer with "{file}"'))
def ui_fileviewer(browser, file):
    url = "{}/fileviewer?file={}".format(portal_url, file)
    browser.visit(url)


@then(parsers.parse('the error message "{message}" is shown'))
def ui_error_message(browser, message):
    assert browser.is_element_present_by_css(".alert-danger", wait_time=5)
    assert browser.is_text_present(message)


@then('the lorem ipsum file is shown')
def ui_fileviewer_file_shown(browser):
    assert browser.is_text_present('lorem ipsum')
