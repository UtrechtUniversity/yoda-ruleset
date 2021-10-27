# coding =utf-8
"""Vault UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_intake.feature')


# GENERIC FUNCTIONS
def get_unscanned_from_error_area_text(browser):
    # Unrecognised and unscanned (17) files or Unrecognised (12) and unscanned (-) files
    error_area_text = browser.find_by_id('scan_result_text')
    parts = error_area_text.value.split(' and ')
    s = parts[1]
    return s[s.find("(") + 1:s.find(")")]


def get_unrecognized_from_error_area_text(browser):
    error_area_text = browser.find_by_id('scan_result_text')
    parts = error_area_text.value.split(' and ')
    s = parts[0]
    first_bracket = s.find("(")
    if first_bracket == -1:
        return "0"
    return s[first_bracket + 1:s.find(")")]


# SCENARIO 1
@when(parsers.parse('activate study "{study}"'))
def ui_intake_activate_study(browser, study):
    dropdown = browser.find_by_id('dropdown-select-study')
    dropdown.click()
    table = browser.find_by_id('select-study')
    rows = table.find_by_tag('tr')
    for row in rows:
        if row.has_class('ta-' + study):
            row.find_by_tag('td').click()
            return True
    assert False


@when(parsers.parse('total datasets is "{dataset_count}"'))
def ui_intake_total_dataset_count(browser, dataset_count):
    dataset_count_area = browser.find_by_id('datatable_info')
    if dataset_count == '0':
        assert dataset_count_area.value == 'No datasets present'
    else:
        assert dataset_count_area.value == "Total datasets: " + dataset_count


@when('unscanned files are present')  # ben ik hier niet de prerequisite aan het testen???
def ui_intake_unscanned_files_present(browser):
    assert int(get_unscanned_from_error_area_text(browser)) > 0


@when('scanned for datasets')
def ui_intake_scanned_for_datasets(browser):
    browser.find_by_id('btn-start-scan').click()


@then('scan button is disabled')
def ui_intake_scan_button_is_disabled(browser):
    assert browser.find_by_id('btn-start-scan').has_class('disabled')


@when('scanning for datasets is successful')
def ui_intake_scanning_is_successful(browser):
    assert browser.is_text_present('Successfully scanned for datasets.', wait_time=20)


@when('unrecognized files are present')
def ui_intake_unrecognized_files_are_present(browser):
    assert int(get_unrecognized_from_error_area_text(browser)) > 0


@when('click for details of first dataset row')
def ui_intake_click_for_details_of_first_dataset_row(browser):
    browser.find_by_id('datatable')[0].click()


@when(parsers.parse('add "{comments}" to comment field and press comment button'))
def ui_intake_add_comments_to_dataset(browser, comments):
    browser.find_by_name('comments').fill(comments)
    browser.find_by_css(".btn-add-comment").click()


@when('check first dataset for locking')
def ui_check_first_dataset_for_locking(browser):
    browser.find_by_css('.cbDataSet')[0].click()


@when(parsers.parse('lock and unlock buttons are "{enabled_state}"'))
def ui_intake_lock_and_unlock_buttons_are(browser, enabled_state):
    if enabled_state == 'enabled':
        assert not browser.find_by_id('btn-unlock').has_class('disabled')
        assert not browser.find_by_id('btn-lock').has_class('disabled')
    else:
        assert browser.find_by_id('btn-unlock').has_class('disabled')
        assert browser.find_by_id('btn-lock').has_class('disabled')


@when('uncheck first dataset for locking')
def ui_uncheck_first_dataset_for_locking(browser):
    # if not checkbox.is_selected() meenemen hier
    browser.find_by_css('.cbDataSet')[0].click()


@when('check all datasets for locking')
def ui_check_all_datasets_for_locking(browser):
    browser.find_by_css('.control-all-cbDataSets').click()


@then('click lock button')
def ui_intake_click_lock_button(browser):
    browser.find_by_id("btn-lock").click()


@then('wait for all datasets to be in locked state successfully')
def ui_intake_wait_all_datasets_in_locked_state(browser):
    assert browser.is_text_present('Successfully locked the selected dataset(s).', wait_time=30)

    assert len(browser.find_by_css('.datasetstatus_locked', wait_time=30)) == 2


@then('wait for all datasets to be in frozen state')
def ui_intake_wait_all_datasets_in_frozen_state(browser):
    i = 0
    no_more_locked_datasets_present = False
    while i < 20:
        time.sleep(20)
        browser.visit(browser.url)
        # if there are no longer datasets in locked state -> frozen or error
        if len(browser.find_by_css('.datasetstatus_locked', wait_time=5)) == 0:  # .datasetstatus_frozen
            no_more_locked_datasets_present = True
            # either datasets are frozen now. Or have been marked errorenous
            break
        i = i + 1
    assert no_more_locked_datasets_present


@then('wait for frozen sets to be added to vault')
def ui_intake_wait_frozen_datasets_to_vault(browser):
    # When all frozen datasets have been moved to the vault only 1 will remain with dataset_status_scanned
    i = 0
    no_more_frozen_datasets_present = False
    while i < 20:
        time.sleep(20)
        browser.visit(browser.url)
        # if there are no longer datasets in locked state -> frozen or error
        if len(browser.find_by_css('.datasetstatus_scanned', wait_time=5)) == 3:  # .datasetstatus_frozen
            no_more_frozen_datasets_present = True
            # either datasets are frozen now. Or have been marked errorenous
            break
        i = i + 1
    assert no_more_frozen_datasets_present


# SCENARIO 2
@when('open intake reporting area')
def ui_intake_open_intake_reporting_area(browser):
    browser.find_by_css('.btn-goto-reports').click()


@when('check reporting result')
def ui_intake_check_reporting_result(browser):
    # classes are part of rows in result table.
    assert len(browser.find_by_css('.dataset-type-counts-raw')) > 0
    assert len(browser.find_by_css('.dataset-type-counts-processed')) == 0
    assert len(browser.find_by_css('.dataset-aggregated-version-raw')) > 0
    assert len(browser.find_by_css('.dataset-aggregated-version-processed')) > 0
    assert len(browser.find_by_css('.dataset-aggregated-version-total')) > 0


@when('export all data and download file')
def ui_intake_export_all_data_and_download_file(browser):
    browser.find_by_css('.btn-export-data').click()


@when('return to intake area')
def ui_intake_return_to_intake_area(browser):
    browser.find_by_css('.btn-goto-intake').click()
