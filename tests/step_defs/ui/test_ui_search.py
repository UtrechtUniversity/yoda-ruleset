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


@when(parsers.parse("the user searches by folder with {folder}"))
def ui_search_folder(browser, folder):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=folder]').click()
    browser.find_by_css('input#search-filter').fill(folder)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when(parsers.parse("the user searches by metadata with {metadata}"))
def ui_search_metadata(browser, metadata):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=metadata]').click()
    browser.find_by_css('input#search-filter').fill(metadata)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when(parsers.parse("the user searches by folder status with {status}"))
def ui_search_status(browser, status):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=status]').click()
    browser.find_by_css('.search-status').click()
    browser.find_by_value(status).click()


@then(parsers.parse("result {result} is found"))
def ui_search_result(browser, result):
    link = []
    while len(link) == 0:
        link = browser.find_by_css(".search-results").links.find_by_partial_text(result)
        if len(link) > 0:
            assert browser.is_text_present(result)
        else:
            browser.find_by_id('search_next').click()
