# coding=utf-8
"""Publication process geo teclab tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from pathlib import Path

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_publication.feature')


@given('all notifications are reset')
@when('all notifications are reset')
def ui_reset_notifcations(browser):
    browser.find_by_id('userDropdown').click()
    browser.links.find_by_partial_text('Notifications')[0].click()

    time.sleep(3)

    # reset all present notifications if any present
    if len(browser.find_by_css('.list-group-item-action')) > 0:
        browser.find_by_id('notifications_dismiss_all').click()


@when(parsers.parse('user checks and clears notifications for status "{status}"'))
def ui_notifications(browser, status):
    time.sleep(3)
    status_text = {'Submitted': ['Data package submitted'],
                   'Accepted': ['Data package secured', 'Data package accepted for vault'],
                   'Submitted for publication': ['Data package submitted for publication', 'Data package secured'],
                   'Approved for publication': ['Data package published', 'Data package approved for publication']}

    browser.find_by_id('userDropdown').click()
    browser.links.find_by_partial_text('Notifications')[0].click()

    time.sleep(3)

    assert len(browser.find_by_css('.list-group-item-action')) == len(status_text[status])

    index = 0
    for status_item in status_text[status]:
        assert browser.find_by_css('.list-group-item-action')[index].value.find(status_item) != -1
        index = index + 1

    browser.find_by_id('notifications_dismiss_all').click()

    time.sleep(3)

    # Check whether all notifications were cleared
    assert len(browser.find_by_css('.list-group-item-action')) == 0


@when('user checks provenance info research')
def ui_check_provenance_research(browser):
    # Check presence and chronological order of provenance
    # precondition is that in the correct research folder already
    # This test can be executed repeatedly as always the n top statuses of the package in research will be checked
    # eventhough the folder is used several times in a different test run
    browser.is_element_visible_by_css('.actionlog-icon', wait_time=5)
    browser.find_by_css('.actionlog-icon').click()
    action_log_rows = browser.find_by_css('.list-group-item-action')
    # Chronological (backwards) status changes
    prov_statuses = ['Secured in vault', 'Accepted for vault', 'Submitted for vault']
    for index in range(0, len(prov_statuses)):
        assert action_log_rows[index].value.find(prov_statuses[index]) != -1


@when('user checks provenance info vault')
def ui_check_provenance_vault(browser):
    # Check presence and chronological order of provenance
    # precondition is that in the correct vault folder (highest level datapackage) already
    browser.is_element_visible_by_css('.actionlog-icon', wait_time=5)
    browser.find_by_css('.actionlog-icon').click()
    action_log_rows = browser.find_by_css('.list-group-item-action')
    # Chronological (backward) status changes
    prov_statuses = ['Published', 'Approved for publication', 'Submitted for publication', 'Secured in vault', 'Accepted for vault', 'Submitted for vault']
    for index in range(0, len(prov_statuses)):
        assert action_log_rows[index].value.find(prov_statuses[index]) != -1


@when(parsers.parse("user downloads file {file}"))
def ui_pub_download_file(browser, file):
    browser.links.find_by_partial_text("original").click()
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()
    browser.find_by_css('#file-browser a.dropdown-item').click()
    browser.back()


@when('user opens landingpage through system metadata')
def ui_pub_open_system_metadata(browser):
    browser.is_element_visible_by_css('.system-metadata', wait_time=5)
    browser.find_by_css('.system-metadata-icon').click()

    link = browser.links.find_by_partial_text('.html')
    link.click()


@then('landingpage content matches yoda-metadata.json')
def ui_pub_check_landingpage_content(browser, tmpdir):
    tags = browser.find_by_css('.tag')
    assert len(tags) == 9  # Directly linked to the yoda-metadata.json file that is put here by ansible for testing purposes.

    # Build list with tag values
    landingpage_tag_values = []
    for i in range(len(tags)):
        landingpage_tag_values.append(tags[i].text)

    # take yoda-metadata.json into account
    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if str(child)[-5:] == ".json":

            # This is dependant on the metadata schema. Now hardcoded and tested only for geo-teclab
            metadata_tags = ['Main_Setting', 'Process_Hazard', 'Geological_Structure', 'Material',
                             'Apparatus', 'Monitoring', 'Software', 'Measured_Property', 'Tag']
            with open(str(child)) as json_file:
                data = json.load(json_file)

                for tag in metadata_tags:
                    if data[tag][0] not in landingpage_tag_values:
                        assert False
            assert True
            return

    raise AssertionError()


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


# folder
@when('user submits the folder')
def ui_folder_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit').click()


# folder
@when('user accepts the folder')
def ui_folder_accept(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-accept').click()


# folder
@then(parsers.parse('the folder status is "{status}"'))
def ui_folder_status(browser, status):
    time.sleep(3)
    badge = browser.find_by_id('statusBadge')
    if status in ["Unlocked", "Unsubmitted"]:
        assert badge.value == ""
    else:
        assert badge.value == status


# vault
@when('user submits the data package for publication')
def ui_data_package_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit-for-publication').click()

    browser.find_by_id('checkbox-confirm-conditions').check()
    browser.find_by_css('.action-confirm-submit-for-publication').click()


@when('user approves the data package for publication')
def ui_data_package_approve(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-approve-for-publication').click()


@then(parsers.parse('the data package status is "{status}"'))
def ui_data_package_status(browser, status):
    for _i in range(30):
        if browser.is_text_present(status, wait_time=3):
            return True
        browser.reload()

    raise AssertionError()
