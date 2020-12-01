# coding=utf-8
"""Folder UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_folder.feature')


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
def ui_folder_status(browser, status):
    time.sleep(2)
    badge = browser.find_by_id('statusBadge')
    if status in ["Unlocked", "Unsubmitted"]:
        assert badge.value == ""
    else:
        assert badge.value == status
