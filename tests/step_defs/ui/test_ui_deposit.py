# coding=utf-8

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
from collections import OrderedDict

from pytest_bdd import (
    parsers,
    given,
    scenarios,
    then,
    when
)

from conftest import api_request, upload_data

scenarios('../../features/ui/ui_deposit.feature')


@when(parsers.parse('user searcher for "{search_argument}"'))
def ui_deposit_open_search(browser, search_argument):
    # browser.find_by_name('q')[0].value = 'LAZLO\r'
    # browser.fill('q', 'title\r\n')
    browser.visit('https://portal.yoda.test/open_search/?q=' + search_argument)
    # browser.type('q', '\r')
    # browser.is_text_present('Search', wait_time=10)


@when('search results are shown')
def ui_deposit_open_search_results(browser):
    # browser.is_text_present('Search', wait_time=10)
    browser.links.find_by_partial_text('title')[0].click()
    # browser.is_text_present('Search', wait_time=10)


@when(parsers.parse('landingpage shows "{data_access}" access'))
def ui_deposit_open_search_complete_data(browser, data_access):
    assert browser.is_text_present(data_access)


@when('all fields contain correct data')
def ui_deposit_open_search_complete_data(browser):
    assert browser.is_text_present('Keyword1')


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
    file = 'BLABLA.BLA'
    return upload_data(
        user,
        file,
        "/deposit-pilot/{}".format(deposit_name)
    )


@given(parsers.parse('"{datapackage_access}" metadata is uploaded'), target_fixture="api_response")
def ui_deposit_metadata_json_upload_on_access(user, deposit_name, datapackage_access):
    cwd = os.getcwd()
    with open("{}/files/{}.json".format(cwd, "dag-" + datapackage_access + "-yoda-metadata")) as f:
        metadata = json.loads(f.read(), object_pairs_hook=OrderedDict)

    return api_request(
        user,
        "meta_form_save",
        {"coll": "/tempZone/home/deposit-pilot/{}".format(deposit_name), "metadata": metadata}
    )


@given(parsers.parse('user clicks new deposit'), target_fixture="deposit_name")
def ui_deposit_click_deposit_on_dp_access(browser):
    # Find the deposit_name for further reference when uploading data
    datapackage = browser.links.find_by_partial_text('deposit-pilot[')[0].value
    browser.links.find_by_partial_text(datapackage)[0].click()
    return datapackage


@when('user goes to submission page')
def ui_deposit_to_submission_page(browser):
    browser.find_by_css('button.btn.btn-primary.pull-right').click()


@when('user accepts terms')
def ui_deposit_accept_terms(browser):
    browser.find_by_id('accept_terms', wait_time=5)[0].click()


@when('user submits data')
def ui_deposit_dp_submission(browser):
    browser.find_by_css('.btn-submit-data')[0].click()


@when('submission is confirmed')
def ui_deposit_dp_submission_confirmed(browser):
    assert browser.is_text_present('Thank you for your deposit')

#-----------
@when('user starts a new deposit')
def ui_deposit_start(browser):
    browser.links.find_by_partial_text('Start new deposit').click()


@when('user clicks on active deposit')
def ui_deposit_click_active(browser):
    browser.links.find_by_partial_text('deposit-pilot[')[0].click()


@when('user clicks on document data button')
def ui_deposit_click_document(browser):
    browser.links.find_by_partial_text('Document data').click()


@then('new deposit is created')
def ui_deposit_created(browser):
    assert browser.is_text_present("deposit-pilot[")


@then('upload data step is shown')
def ui_deposit_upload_data_shown(browser):
    assert browser.is_text_present("Upload data")


@then('document data step is shown')
def ui_deposit_document_data(browser):
    assert browser.is_text_present("Upload data")
