# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_folder.feature')


@given('user "<user>" is logged in')
@given(parsers.parse('user "{user}" is logged in'))
def ui_login(browser, user):
    url = "https://portal.yoda.test/user/login"
    browser.visit(url)

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)

    # Fill in password
    browser.find_by_id('f-login-password').fill('test')

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()


@given(parsers.parse('module "{module}" module is shown'))
def ui_module_shown(browser, module):
    url = "https://portal.yoda.test/{}".format(module)
    browser.visit(url)


@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    link = []
    while len(link) == 0:
        link = browser.links.find_by_partial_text(folder)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()


@when('user locks the folder')
def ui_folder_lock(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-lock').click()


@when('user unlocks the folder')
def ui_folder_unlock(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-unlock').click()


@when('user submits the folder')
def ui_folder_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit').click()


@when('user unsubmits the folder')
def ui_folder_unsubmit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-unsubmit').click()


@when('user rejects the folder')
def ui_folder_reject(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-reject').click()


@when('user accepts the folder')
def ui_folder_accept(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-accept').click()


@then(parsers.parse('the folder status is "{status}"'))
def ui_module_shown(browser, status):
    time.sleep(2)
    badge = browser.find_by_id('statusBadge')
    if status in ["Unlocked", "Unsubmitted"]:
        assert badge.value == ""
    else:
        assert badge.value == status
