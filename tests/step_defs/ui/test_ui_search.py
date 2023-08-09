# coding=utf-8
"""Search UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)
from selenium.webdriver.common.keys import Keys

scenarios('../../features/ui/ui_search.feature')


@when(parsers.parse("the user searches by filename with {file}"))
def ui_search_file(browser, file):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=filename]').click()
    browser.find_by_css('input#search-filter').fill(file)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when(parsers.parse("the user top-searches by filename with {file}"))
def ui_search_top_file(browser, file):
    browser.find_by_css('.container button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=filename]').click()
    browser.find_by_css('input#q').fill(file)
    browser.find_by_css('input#q').type(Keys.RETURN)


@when(parsers.parse("the user searches by folder with {folder}"))
def ui_search_folder(browser, folder):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=folder]').click()
    browser.find_by_css('input#search-filter').fill(folder)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when(parsers.parse("the user top-searches by folder with {folder}"))
def ui_search_top_folder(browser, folder):
    browser.find_by_css('.container button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=folder]').click()
    browser.find_by_css('input#q').fill(folder)
    browser.find_by_css('input#q').type(Keys.RETURN)


@when(parsers.parse("the user searches by metadata with {metadata}"))
def ui_search_metadata(browser, metadata):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=metadata]').click()
    browser.find_by_css('input#search-filter').fill(metadata)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when(parsers.parse("the user top-searches by metadata with {metadata}"))
def ui_search_top_metadata(browser, metadata):
    browser.find_by_css('.container button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=metadata]').click()
    browser.find_by_css('input#q').fill(metadata)
    browser.find_by_css('input#q').type(Keys.RETURN)


@when(parsers.parse("the user searches by folder status with {status}"))
def ui_search_status(browser, status):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=status]').click()
    browser.find_by_css('.search-status').click()
    browser.find_by_value(status).click()


@when(parsers.parse("the user top-searches by folder status with {status}"))
def ui_search_top_status(browser, status):
    browser.find_by_css('.container button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=status]').click()
    browser.find_by_css('.top-search-status').click()
    browser.find_by_value(status).click()


@then(parsers.parse("result {file} is found"))
def ui_search_result(browser, file):
    # no need to step through the list as the results are from searching on this keyword
    for link in browser.find_by_css("table#search tr td"):
        if file in link.value:
            assert True
            return True
    assert False
    # if rows are present, that is good enough
    assert len(link) == 0
