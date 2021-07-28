# coding=utf-8
"""Login OIDC UI feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    when,
)

from conftest import password, portal_url


scenarios('../../features/ui/ui_login_redirect.feature')

restricted_page = "{}/test".format(portal_url)


@when('user "<user>" logs in after being redirected')
def ui_login_directly(browser, user):
    assert "{}/user/gate".format(portal_url) in browser.url

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)
    browser.find_by_id('f-login-submit').click()

    # Fill in password
    browser.find_by_id('f-login-password').fill(password)

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()
