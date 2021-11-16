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


@then('user browses to subfolder "<folder_new>"')
@when('user browses to subfolder "<folder_new>"')
def ui_browse_newsubfolder(browser, folder_new):
    time.sleep(3)
    browser.links.find_by_partial_text(folder_new).click()


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


@when('user multi-select moves files / folders to "<folder_new>"')
def ui_research_multi_move(browser, folder_new):
    browser.find_by_css('input[data-name="testdata"]').click()
    browser.find_by_css('input[data-name="yoda-metadata.json"]').click()
    browser.find_by_id('multiSelect').click()
    browser.find_by_css('a.multiple-move').click()
    time.sleep(3)
    browser.links.find_by_partial_text(folder_new).click()
    browser.find_by_css('.dlg-action-button').click()
    time.sleep(5)
    browser.find_by_id('finishMultiSelect').click()


@when('user multi-select copies files / folders to "<folder>"')
def ui_research_multi_copy(browser, folder):
    browser.find_by_css('input[data-name="testdata"]').click()
    browser.find_by_css('input[data-name="yoda-metadata.json"]').click()
    browser.find_by_id('multiSelect').click()
    browser.find_by_css('a.multiple-copy').click()
    time.sleep(3)
    browser.find_by_css('[data-path="/{}"]'.format(folder)).click()
    browser.find_by_css('.dlg-action-button').click()
    time.sleep(3)
    browser.find_by_id('finishMultiSelect').click()


@when('user multi-select deletes files / folders')
def ui_research_multi_delete(browser, folder):
    browser.find_by_css('input[data-name="testdata"]').click()
    browser.find_by_css('input[data-name="yoda-metadata.json"]').click()
    browser.find_by_id('multiSelect').click()
    browser.find_by_css('a.multiple-delete').click()
    browser.find_by_css('.dlg-action-button').click()
    time.sleep(3)
    browser.find_by_id('finishMultiSelect').click()


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


@then('files / folders exist in "<folder>"')
def ui_research_files_folders_exist(browser, folder):
    browser.is_text_present(folder)
    browser.is_text_present("testdata")
    browser.is_text_present("yoda-metadata.json")


@then('files / folders exist in "<folder_new>"')
def ui_research_files_folders_new_exist(browser, folder_new):
    browser.is_text_present(folder_new)
    browser.is_text_present("testdata")
    browser.is_text_present("yoda-metadata.json")


@then('files / folders do not exist in "<folder_new>"')
def ui_research_files_folders_new_not_exist(browser, folder_new):
    browser.is_text_present(folder_new)
    browser.is_text_not_present("testdata")
    browser.is_text_not_present("yoda-metadata.json")


@then('files / folders do not exist in "<subfolder>"')
def ui_research_files_folders_sub_not_exist(browser, subfolder):
    browser.is_text_present(subfolder)
    browser.is_text_not_present("testdata")
    browser.is_text_not_present("yoda-metadata.json")
