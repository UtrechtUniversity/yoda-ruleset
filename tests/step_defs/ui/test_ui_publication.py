# coding=utf-8
"""Publication process geo teclab tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json, os, time
from pathlib import Path

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_publication.feature')


@then('user downloads relevant files of datapackage')
def ui_pub_download_relevant_files(browser):
    # License file and yoda-metadata.json are present at toplevel
    assert len(browser.find_by_css('.fa-file-o')) == 2
	
    # Download each file - only yoda-metadata is required for testing purposes
    # But for some reason it was impossible to distinghuish one from the other.
    browser.find_by_css('.fa-ellipsis-h')[0].click()
    browser.links.find_by_partial_text('Download')[0].click()

    browser.find_by_css('.fa-ellipsis-h')[1].click()
    browser.links.find_by_partial_text('Download')[1].click()


@then('user opens landingpage through system metadata')
def ui_pub_open_system_metadata(browser):
    browser.find_by_css('.system-metadata-icon')[0].click()

    link = browser.links.find_by_partial_text('allinone')
    link.click()


@then('user checks landingpage content')
def ui_pub_check_landingpage_content(browser, tmpdir):
    tags = browser.find_by_css('.tag')
    assert len(tags) == 10  # schema dependant

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
            metadata_tags = ['Main_Setting', 'Process_Hazard', 'Geological_Structure', 'Geomorphical_Feature',
                             'Material', 'Apparatus', 'Monitoring', 'Software', 'Measured_Property', 'Tag']
            with open(str(child)) as json_file:
                data = json.load(json_file)

                for tag in metadata_tags:
                    if data[tag][0] not in landingpage_tag_values:
                        assert False
            assert True
            return

    raise AssertionError()


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
    time.sleep(10)
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
    for _i in range(25):
        if browser.is_text_present(status, wait_time=3):
            return True
        browser.reload()

    raise AssertionError()


@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    # browser.links.find_by_partial_text(folder).click()

    link = []
    while len(link) == 0:
        link = browser.links.find_by_partial_text(folder)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()

    browser.find_by_css('.sorting_asc').click()

    browser.links.find_by_partial_text(folder)[0].click()

