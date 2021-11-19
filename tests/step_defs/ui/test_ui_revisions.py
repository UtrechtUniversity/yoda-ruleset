# coding=utf-8
"""Revisions UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
    when,
)
from selenium.webdriver.common.keys import Keys

scenarios('../../features/ui/ui_revisions.feature')


@when('the user searches revision by name with "<name>"')
def ui_revisions_search(browser, name):
    browser.find_by_css('.page button.dropdown-toggle').click()
    browser.find_by_css('a.dropdown-item[data-type=revision]').click()
    browser.find_by_css('input#search-filter').fill(name)
    browser.find_by_css('input#search-filter').type(Keys.RETURN)


@when('user restores revision "<revision>"')
def ui_revisions_restore(browser, revision):
    link = []
    while len(link) == 0:
        link = browser.find_by_css("#file-browser").links.find_by_partial_text(revision)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()

    browser.find_by_css(".btn-revision-select-dialog").click()
    browser.find_by_css("#btn-restore").click()
    browser.find_by_css("#btn-restore-overwrite").click()


@then('revision "<revision>" is found')
def ui_revisions_found(browser, revision):
    link = []
    while len(link) == 0:
        link = browser.find_by_css("#file-browser").links.find_by_partial_text(revision)
        if len(link) > 0:
            assert link.value == revision
        else:
            browser.find_by_id('file-browser_next').click()


@then('revision is restored')
def ui_revisions_restored(browser):
    assert browser.is_text_present("Successfully made a copy of revision")
