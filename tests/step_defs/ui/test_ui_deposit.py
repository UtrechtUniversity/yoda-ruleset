# coding=utf-8

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from collections import OrderedDict

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when
)
from selenium.webdriver.common.keys import Keys

from conftest import api_request, upload_data

scenarios('../../features/ui/ui_deposit.feature')


@when(parsers.parse('user searches for "{search_argument}"'))
def ui_deposit_open_search(browser, search_argument):
    browser.fill('q', search_argument)
    browser.find_by_name('q').type(Keys.RETURN)


@when(parsers.parse('clicks on "{title}" data package'))
def ui_deposit_open_search_results(browser, title):
    browser.links.find_by_partial_text(title)[0].click()


@when(parsers.parse('landingpage shows "{data_access}" access'))
def ui_deposit_open_search_data_access_type_visible(browser, data_access):
    assert browser.is_text_present(data_access)


@when('all fields contain correct data')
def ui_deposit_open_search_contains_correct_data(browser):
    required_text = ['Jane Doe (Principal Investigator)',
                     'UI test',
                     'Aut aspernatur quia perferendis et',
                     'Keyword1',
                     'Earth sciences - Geochemistry',
                     'Project1',
                     'Jane Doe, Utrecht University, Principal Investigator',
                     'John Doe',
                     '2000-01-01 - 2010-01-01',
                     'Reference to a publication',
                     'Another reference to a publication']
    # Retention not fully / correctly implemented in open_search
    # '2022-03-10',
    # '2042-03-10 (20 years)']
    for text in required_text:
        if not browser.is_text_present(text):
            assert False
    assert True


@when('user copies identifier to clipboard')
def ui_user_clicks_copy_reference(browser):
    browser.find_by_css('.btn-copy-to-clipboard')[0].click()
    assert browser.find_by_text('DAG permalink identifier has been copied to the clipboard')


@when('user clicks for map details')
def ui_user_click_map_details(browser):
    browser.find_by_css('.show-map')[0].click()
    assert browser.find_by_tag('h5').value == 'Europe'
    browser.find_by_css('button.btn.btn-secondary')[0].click()


@when(parsers.parse('user clicks for data access with "{title}" in title'))
def ui_user_clicks_for_data_access(browser, title):
    browser.find_by_css('.btn-show-file-browser')[0].click()
    assert browser.is_text_present(title)


@given('data file is uploaded to deposit', target_fixture="api_response")
def api_deposit_file_upload(user, deposit_name):
    file = 'ui_test.file'
    return upload_data(
        user,
        file,
        "/deposit-pilot/{}".format(deposit_name)
    )


@given('"<data_access_restriction>" metadata is uploaded', target_fixture="api_response")
def ui_deposit_metadata_json_upload_on_access(user, deposit_name, data_access_restriction):
    cwd = os.getcwd()
    with open("{}/files/dag-0-{}.json".format(cwd, data_access_restriction)) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    return api_request(
        user,
        "meta_form_save",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name), "metadata": metadata}
    )


@given(parsers.parse('user clicks new deposit'), target_fixture="deposit_name")
def ui_deposit_click_deposit_on_dp_access(browser):
    # Find the deposit_name for further reference when uploading data
    # strip away /deposit-pilot/ to get to the deposit name
    datapackage = browser.links.find_by_partial_text('[No title]')[0]['data-path'][15:]

    browser.links.find_by_partial_text('[No title]')[0].click()

    return datapackage


@when('user clicks on deposit containing "<data_access_restriction>" in title')
def ui_deposit_click_deposit_in_overview(browser, data_access_restriction):
    package_title_contains = 'UI test ' + data_access_restriction.title()
    browser.links.find_by_partial_text(package_title_contains)[0].click()


@when('user goes to submission page')
def ui_deposit_to_submission_page(browser):
    browser.find_by_css('button.btn.btn-primary.float-end', wait_time=10).click()


@when('user accepts terms')
def ui_deposit_accept_terms(browser):
    browser.find_by_id('accept_terms', wait_time=5)[0].click()


@when('user submits data')
def ui_deposit_dp_submission(browser):
    browser.find_by_css('.btn-submit-data')[0].click()


@when('submission is confirmed')
def ui_deposit_dp_submission_confirmed(browser):
    time.sleep(10)
    assert browser.is_text_present('Thank you for your deposit')


@when('user starts a new deposit')
def ui_deposit_start(browser):
    browser.links.find_by_partial_text('Start new deposit').click()


@when('user clicks on active deposit')
def ui_deposit_click_active(browser):
    # browser.links.find_by_partial_text('deposit-pilot[')[0].click()
    browser.links.find_by_partial_text('[No title]')[0].click()


@when('user clicks on document data button')
def ui_deposit_click_document(browser):
    browser.links.find_by_partial_text('Document data').click()


@then('new deposit is created')
def ui_deposit_created(browser):
    # assert browser.is_text_present("deposit-pilot[")
    assert browser.is_text_present('[No title]')


@then('upload data step is shown')
def ui_deposit_upload_data_shown(browser):
    assert browser.is_text_present("Upload data")


@then('document data step is shown')
def ui_deposit_document_data(browser):
    assert browser.is_text_present("Upload data")
