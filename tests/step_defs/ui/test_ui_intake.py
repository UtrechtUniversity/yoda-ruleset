# coding =utf-8
"""Vault UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_intake.feature')


########################## GENERIC FUNCTIONS
def get_unscanned_from_error_area_text():
    # Unrecognised and unscanned (17) files or Unrecognised (12) and unscanned (-) files
    error_area_text = browser.find_by_id('scan_result_text')
    parts = error_area.value.split(' and ')
    s = parts[0]
    return s[s.find("(")+1:s.find(")")]


def get_unrecognized_from_error_area_text():
    error_area_text = browser.find_by_id('scan_result_text')
    parts = error_area.value.split(' and ')
    s = parts[1]
    first_bracket = s.find("(")
    if first_bracket == -1:
	    return ""
    return s[first_bracket + 1:s.find(")")]


####################### SCENARIOS ##################
# SCENARIO 1 
	#	And study "<study>" is active - hierin switchen als niet actief is
@when('activate "<study>"')
def ui_intake_activate_study(browser, study):
	study = study # NU FF NIKS DOEN

	
@when('total datasets is "{dataset_count}"') # text is hardcoded in feature -> NOT variable
def ui_intake_total_dataset_count(browser, dataset_count):
    dataset_count_area = browser.find_by_id('datatable_info')   # => 'No datasets present'
    assert dataset_count_area.value == "<span>" + dataset_count + "</span>"   # Dit moet mooier??

		
@when('unscanned files are present')  # ben ik hier niet de prerequisite aan het testen???
def ui_intake_unscanned_files_present(browser):
	assert int(get_unscanned_from_error_area_text()) > 0


@when('scanned for datasets')
def ui_intake_scanned_for_datasets(browser):
    browser.find_by_id('#btn-start-scan').click()


@when('scan button is disabled')
def ui_intake_scan_button_is_disabled(browser):
    assert not browser.find_by_id('#btn-start-scan').is_enabled()


@then('Then scanning for datasets is successfull')
def ui_intake_scanning_is_successfull(browser):
	      ## browser.is_element_visible_by_css('.system-metadata', wait_time=5)
	      #.alert alert-success
	assert browser.is_text_present('Successfully scanned for datasets.', wait_time=10)


@then('datasets are present')
def ui_intake_datasets_are_present(browser):
    browser.find_by_css('dataTables_info')
    dataset_count_area = browser.find_by_id('datatable_info')  # => 'No datasets present'
    assert dataset_count_area.value == "<span>" + dataset_count + "</span>"   # Dit moet mooier?? OPLOSSEN


@when('unrecognized files are present')
def ui_intake_unrecognized_files_are_present(browser):
#	total_error_count = browser.find_by_id('datatable_unrecognised_info')
    assert int(get_unrecognized_from_error_area_text()) > 0

	
@when('click for details of first dataset row')
def ui_intake_click_for_details_of_first_dataset_row(browser):
    browser.find_by_css('details-control')[0].first.click()


@when('add "{comments}" to comment field and press comment button')
def ui_intake_add_comments_to_dataset(browser, comments):
	browser.find_by_name('comments').fill(comments)
	browser.find_by_css("btn-add-comment").click()


@when('check first dataset for locking')
def ui_check_first_dataset_for_locking(browser):
    browser.find_by_css('.cbDataSet')[0].click()


@when('lock and unlock buttons are "{enabled_state}"')
def ui_intake_lock_and_unlock_buttons_are(browser, enabled_state):
	browser.find_by_id('#btn-unlock')
	browser.find_by_id('#btn-lock')


@when('uncheck first dataset for locking')
def ui_uncheck_first_dataset_for_locking(browser):
    # if not checkbox.is_selected() meenemen hier
    browser.find_by_css('.cbDataSet')[0].click() # click again


@when('check all datasets for locking')
def ui_check_all_datasets_for_locking(browser):
    browser.find_by_css('#control-all-cbDataSets').click()


@when('click lock button')
def ui_intake_click_lock_button(browser):
    browser.find_by_id("btn-lock").click()

		
@when('wait for all datasets to be in locked state successfully')
def ui_intake_wait_all_datasets_in_locked_state(browser):		
    browser.is_text_present('Successfully locked the selected dataset(s).', wait_time=30)

    assert   browser.is_element_present_by_css('datasetstatus_locked')


# SCENARIO 2
@when('open intake reporting area')
def ui_intake_open_intake_reporting_area(browser):
    browser.find_by_css('btn-goto-reports').click()


@when('check reporting result')
def ui_intake_check_reporting_result(browser):
    # classes are part of rows in result table.
    assert len(browser.find_by_css('dataset-type-counts-raw')) > 0
    assert len(browser.find_by_css('dataset-type-counts-processed')) > 0
    assert len(browser.find_by_css('dataset-aggregated-version-raw')) > 0
    assert len(browser.find_by_css('dataset-aggregated-version-processed')) > 0
    assert len(browser.find_by_css('dataset-aggregated-version-total')) > 0


@when('export all data and download file')
def ui_intake_export_all_data_and_download_file(browser):
    browser.find_by_css('btn-export-data').click()


@when('return to intake area')
def ui_intake_return_to_intake_area(browser):
    browser.find_by_css('btn-goto-intake').click()

