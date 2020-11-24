# coding=utf-8
"""Vault UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    when,
)

scenarios('../../features/ui/ui_vault.feature')


@given('user "<user>" is logged in')
def ui_login(browser, user):
    url = "https://portal.yoda.test/user/login"
    browser.visit(url)

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)

    # Fill in password
    browser.find_by_id('f-login-password').fill('test')

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()


@when(parsers.parse('module "{module}" module is shown'))
def ui_module_shown(browser, module):
    url = "https://portal.yoda.test/{}".format(module)
    browser.visit(url)


@when('user browses to data package "<data_package>"')
def ui_browse_data_package(browser, data_package):
    browser.links.find_by_partial_text(data_package).click()
