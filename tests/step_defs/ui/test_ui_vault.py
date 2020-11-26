# coding=utf-8
"""Vault UI feature tests."""

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

scenarios('../../features/ui/ui_vault.feature')


@when('user browses to data package in "<vault>"')
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


@when('user submits the data package for publication')
def ui_data_package_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit-for-publication').click()

    browser.find_by_id('checkbox-confirm-conditions').check()
    browser.find_by_css('.action-confirm-submit-for-publication').click()


@when('user cancels publication of the data package')
def ui_data_package_cancel(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-cancel-publication').click()


@when('user approves the data package for publication')
def ui_data_package_approve(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-approve-for-publication').click()


@then(parsers.parse('the data package status is "{status}"'))
def ui_data_package_status(browser, status):
    browser.is_text_present(status, wait_time=10)
