# coding=utf-8
"""Login OIDC UI feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_login_oidc.feature')


@given('login page is shown')
def ui_login(browser):
    browser.is_text_present("Login to Yoda")


@when('user clicks login with OIDC')
def ui_login_oidc(browser):
    # Find and click the 'OIDC Sign in' button
    browser.find_by_css('.btn-secondary').click()


@when('user "<user>" follows OIDC login process')
def ui_login_oidc_form(browser, user):
    # Fill login form
    browser.find_by_name('email').fill(user)
    browser.find_by_name('password').fill('5150time')

    # Click login button
    browser.find_by_id('login-submit').click()


@then('user "<user>" is logged in')
def ui_user_login(browser, user):
    assert browser.is_text_present("{}".format(user), wait_time=10)
