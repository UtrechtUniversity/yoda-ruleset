# coding=utf-8
"""Login UI feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
)

from conftest import portal_url, roles

scenarios('../../features/ui/ui_login.feature')


@given('the user is at the login gate')
def ui_gate(browser):
    url = "{}/user/gate".format(portal_url)
    browser.visit(url)


@given('the user is redirected to the login page')
@then('the user is redirected to the login page')
def ui_login_assert_login_page(browser):
    assert (
        "{}/user/login".format(portal_url) in browser.url
        or "{}/user/gate".format(portal_url) in browser.url)


@then(parsers.parse("user {user} is logged in"))
def ui_user_login(browser, user):
    assert browser.is_text_present("{}".format(roles[user]["username"]), wait_time=10)


@then("incorrect username / password message is shown")
def ui_user_incorrect(browser):
    assert browser.is_text_present("Username/password was incorrect", wait_time=10)


@then(parsers.parse("the user is redirected to page {page}"))
def ui_user_redirected(browser, page):
    target = "{}{}".format(portal_url, page)

    assert browser.url == target
