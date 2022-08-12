# coding=utf-8
"""Folder UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_folder.feature')


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
    time.sleep(5)
    badge = browser.find_by_id('statusBadge')
    if status in ["Unlocked", "Unsubmitted"]:
        assert badge.value == ""
    else:
        assert badge.value == status


@then(parsers.parse('provenance log includes "{status}"'))
def ui_provenance_log(browser, status):
    # Check presence of provenance log item.
    # This test can be executed repeatedly as always the n top statuses of the package in research will be checked
    # eventhough the folder is used several times in a different test run
    browser.find_by_css('.actionlog-icon')[0].click()
    prov_statuses = {"Locked": "Locked",
                     "Unlocked": "Unlocked",
                     "Submitted": "Submitted for vault",
                     "Unsubmitted": "Unsubmitted for vault",
                     "Rejected": "Rejected for vault",
                     "Accepted": "Accepted for vault",
                     "Secured": "Secured in vault"}

    for _i in range(25):
        if len(browser.find_by_css('.list-group-item-action')):
            action_log_rows = browser.find_by_css('.list-group-item-action')
            break
        else:
            time.sleep(1)

    for index in range(0, len(prov_statuses)):
        if action_log_rows[index].value.find(prov_statuses[status]) != -1:
            return True
