# coding=utf-8
"""Admin UI feature tests."""

__copyright__ = "Copyright (c) 2024, Utrecht University"
__license__ = "GPLv3, see LICENSE"

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)
import time
from conftest import portal_url

scenarios("../../features/ui/ui_admin.feature")


@when(parsers.parse("user opens link to admin page"))
def ui_admin_access(browser):
    url = "{}/admin".format(portal_url)
    time.sleep(10)  # FIXME:In case of slow VM machine
    browser.visit(url)


@then("the text Administration is shown")
def ui_admin_administration_present(browser):
    h1_tags = browser.find_by_tag("h1")  # Avoid finding the one in dropdown
    found = any("administration" in h1.text.lower() for h1 in h1_tags)
    assert found


@then("Administration option is available in the menu dropdown")
def ui_admin_administration_dropdown_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    found = browser.is_element_present_by_xpath(xpath)
    assert found


@then("Administration option is not available in the menu dropdown")
def ui_admin_administration_dropdown_not_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    not_found = browser.is_element_not_present_by_xpath(xpath)
    assert not_found


@then("the text Access forbidden is shown")
def ui_admin_access_forbidden(browser):
    assert browser.is_text_present("Access forbidden")
