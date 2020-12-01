# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_research.feature')


@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    browser.links.find_by_partial_text(folder).click()


@when('user adds a new folder "<folder_new>"')
def ui_research_folder_add(browser, folder_new):
    browser.find_by_css('.folder-create').click()
    browser.find_by_id('path-folder-create').fill(folder_new)
    browser.find_by_css('.btn-confirm-folder-create').click()


@when('user renames folder "<folder_old>" to "<folder_new>"')
def ui_research_folder_rename(browser, folder_old, folder_new):
    browser.find_by_css('button[data-name={}]'.format(folder_old)).click()
    browser.find_by_css('a.folder-rename[data-name={}]'.format(folder_old)).click()
    browser.find_by_id('folder-rename-name').fill(folder_new)
    browser.find_by_css('.btn-confirm-folder-rename').click()


@when('user deletes folder "<folder_delete>"')
def ui_research_folder_delete(browser, folder_delete):
    browser.find_by_css('button[data-name={}]'.format(folder_delete)).click()
    browser.find_by_css('a.folder-delete[data-name={}]'.format(folder_delete)).click()
    browser.find_by_css('.btn-confirm-folder-delete').click()


@then('folder "<folder_new>" exists in "<folder>"')
def ui_research_folder_exists(browser, folder_new, folder):
    browser.is_text_present(folder)
    browser.is_text_present(folder_new)


@then('folder "<folder_delete>" does not exists in "<folder>"')
def ui_research_folder_not_exists(browser, folder_delete, folder):
    browser.is_text_present(folder)
    browser.is_text_not_present(folder_delete)
