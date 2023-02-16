# coding=utf-8
"""Vault Archive UI feature tests."""

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_vault_archive.feature')


@when(parsers.parse("user browses to data package in {vault}"))
def ui_browse_data_package(browser, vault):
    link = []
    while len(link) == 0:
        link = browser.links.find_by_partial_text(vault)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()

    browser.find_by_css('.sorting_asc').click()

    research = vault.replace("vault-", "research-")
    data_packages = browser.links.find_by_partial_text(research)
    data_packages.click()


@when('user submits the data package for archival')
def ui_data_package_archive(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-vault-archival').click()


@when('user confirms archival of data package')
def ui_data_package_archival_agree(browser):
    browser.find_by_css('.action-confirm-vault-archival').click()


@when('user submits the data package for unarchival')
def ui_data_package_unarchival(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-vault-unarchive').click()


@when('user confirms unarchival of data package')
def ui_data_package_unarchival_agree(browser):
    browser.find_by_css('.action-confirm-vault-unarchive').click()


@then(parsers.parse('the data package archive status is "{status}"'))
def ui_data_package_archive_status(browser, status):
    for _i in range(36):
        if browser.is_text_present(status, wait_time=10):
            return True
        browser.reload()

    raise AssertionError()


@then(parsers.parse('provenance log includes "{status}"'))
def ui_provenance_log(browser, status):
    # Check presence of provenance log item.
    # This test can be executed repeatedly as always the n top statuses of the package in research will be checked
    # eventhough the folder is used several times in a different test run
    browser.find_by_css('.actionlog-icon')[0].click()
    prov_statuses = {"Scheduled for archive": "Archive scheduled",
                     "Archived": "Archive completed",
                     "Scheduled for unarchive": "Unarchive scheduled",
                     "Unarchived": "Unarchive completed"}

    for _i in range(36):
        if len(browser.find_by_css('.list-group-item-action')):
            action_log_rows = browser.find_by_css('.list-group-item-action')
            break
        else:
            time.sleep(10)

    for index in range(0, len(prov_statuses)):
        if action_log_rows[index].value.find(prov_statuses[status]) != -1:
            return True
