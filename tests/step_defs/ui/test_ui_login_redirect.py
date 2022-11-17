# coding=utf-8
"""Login redirect UI feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    when,
)

from conftest import portal_url, roles


scenarios('../../features/ui/ui_login_redirect.feature')

restricted_page = "{}/test".format(portal_url)


@when(parsers.parse("user {user} logs in after being redirected"))
def ui_login_directly(browser, user):
    assert "{}/user/gate".format(portal_url) in browser.url

    # Fill in username
    browser.find_by_id('f-login-username').fill(roles[user]["username"])
    browser.find_by_id('f-login-submit').click()

    # Fill in password
    browser.find_by_id('f-login-password').fill(roles[user]["password"])

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()
