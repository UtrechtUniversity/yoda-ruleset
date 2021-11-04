# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_research.feature')


@then('user browses to subfolder "<subfolder>"')
@when('user browses to subfolder "<subfolder>"')
def ui_browse_subfolder(browser, subfolder):
    time.sleep(3)
    browser.links.find_by_partial_text(subfolder).click()


@when('user copies file "<file>" to "<folder>"')
def ui_research_file_copy(browser, file, folder):
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()
    browser.find_by_css('a.file-copy[data-name="{}"]'.format(file)).click()
    time.sleep(3)
    browser.find_by_css('[data-path="/{}"]'.format(folder)).click()
    browser.find_by_css('.dlg-action-button').click()


@when('user moves file "<file>" to "<subfolder>"')
def ui_research_file_move(browser, file, subfolder):
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()
    browser.find_by_css('a.file-move[data-name="{}"]'.format(file)).click()
    time.sleep(3)
    browser.links.find_by_partial_text(subfolder).click()
    browser.find_by_css('.dlg-action-button').click()


@when('user renames file "<file>" to "<file_renamed>"')
def ui_research_file_rename(browser, file, file_renamed):
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()
    browser.find_by_css('a.file-rename[data-name="{}"]'.format(file)).click()
    browser.find_by_id('file-rename-name').fill(file_renamed)
    browser.find_by_css('.btn-confirm-file-rename').click()


@when('user deletes file "<file>"')
def ui_research_file_delete(browser, file):
    browser.find_by_css('button[data-name="{}"]'.format(file)).click()
    browser.find_by_css('a.file-delete[data-name="{}"]'.format(file)).click()
    browser.find_by_css('.btn-confirm-file-delete').click()


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


@when('user copies folder "<folder_old>" to "<folder_new>"')
def ui_research_folder_copy(browser, folder_old, folder_new):
    browser.find_by_css('button[data-name={}]'.format(folder_old)).click()
    browser.find_by_css('a.folder-copy[data-name={}]'.format(folder_old)).click()
    time.sleep(3)
    browser.links.find_by_partial_text(folder_new).click()
    browser.find_by_css('.dlg-action-button').click()


@when('user moves folder "<folder_old>" to "<folder_new>"')
def ui_research_folder_move(browser, folder_old, folder_new):
    browser.find_by_css('button[data-name={}]'.format(folder_old)).click()
    browser.find_by_css('a.folder-move[data-name={}]'.format(folder_old)).click()
    time.sleep(3)
    browser.links.find_by_partial_text(folder_new).click()
    browser.find_by_css('.dlg-action-button').click()


@when('user deletes folder "<folder_delete>"')
def ui_research_folder_delete(browser, folder_delete):
    browser.find_by_css('button[data-name={}]'.format(folder_delete)).click()
    browser.find_by_css('a.folder-delete[data-name={}]'.format(folder_delete)).click()
    browser.find_by_css('.btn-confirm-folder-delete').click()


@then('user browses to subfolder "<folder_new>"')
def ui_browse_newsubfolder(browser, folder_new):
    time.sleep(3)
    browser.links.find_by_partial_text(folder_new).click()


@then('folder "<folder_new>" exists in "<folder>"')
def ui_research_folder_exists(browser, folder_new, folder):
    browser.is_text_present(folder)
    browser.is_text_present(folder_new)


@then('folder "<folder_new>" exists in "<folder_old>"')
def ui_research_newfolder_exists(browser, folder_new, folder_old):
    browser.is_text_present(folder_old)
    browser.is_text_present(folder_new)


@then('folder "<folder_delete>" does not exists in "<folder>"')
def ui_research_folder_not_exists(browser, folder_delete, folder):
    browser.is_text_present(folder)
    browser.is_text_not_present(folder_delete)


@then('file "<file>" exists in folder')
def ui_research_file_exists(browser, file):
    browser.is_text_present(file)


@then('file "<file>" does not exist in folder')
def ui_research_file_not_exists(browser, file):
    browser.is_text_not_present(file)
