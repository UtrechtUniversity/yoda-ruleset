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
    url = f"{portal_url}/user/gate"
    browser.visit(url)


@given('the user is redirected to the login page')
@then('the user is redirected to the login page')
def ui_login_assert_login_page(browser):
    assert (
        f"{portal_url}/user/login" in browser.url
        or f"{portal_url}/user/gate" in browser.url)


@then(parsers.parse("user {user} is logged in"))
def ui_user_login(browser, user):
    assert browser.is_text_present(f"{roles[user]['username']}", wait_time=10)


@then("incorrect username / password message is shown")
def ui_user_incorrect(browser):
    assert browser.is_text_present("Username/password was incorrect", wait_time=10)


@then("user not in Yoda message is shown")
def ui_user_not_in_instance(browser):
    assert browser.is_element_present_by_id("alert-user-not-in-instance", wait_time=10)


@then(parsers.parse("the user is redirected to page {page}"))
def ui_user_redirected(browser, page):
    target = f"{portal_url}{page}"

    assert browser.url.startswith(target)
