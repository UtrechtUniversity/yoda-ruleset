# coding=utf-8
"""Login UI feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import portal_url

scenarios('../../features/ui/ui_login.feature')

restricted_page = "{}/test".format(portal_url)


@given(parsers.parse("the user {user} can start the OIDC flow"))
def ui_start_oidc(browser, user):
    url = "{}/user/gate".format(portal_url)
    browser.visit(url)
    input_username = browser.find_by_id('f-login-username')
    input_username.fill(user)
    browser.find_by_id('f-login-submit').click()


@given('the user is at the login gate')
def ui_gate(browser):
    url = "{}/user/gate".format(portal_url)
    browser.visit(url)


@when('user clicks login with OIDC')
def ui_login_oidc(browser):
    # Find and click the 'OIDC Sign in' button
    browser.find_by_css('.btn-secondary').click()


@when(parsers.parse("user {user} follows OIDC login process"))
def ui_login_oidc_form(browser, user):
    # Fill login form
    browser.find_by_name('email').fill(user)
    browser.find_by_name('password').fill('5150time')

    # Click login button
    browser.find_by_id('login-submit').click()


@then(parsers.parse("user {user} is logged in"))
def ui_user_login(browser, user):
    assert browser.is_text_present("{}".format(user), wait_time=10)
