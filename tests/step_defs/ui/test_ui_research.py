# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_research.feature')


@when('user clicks rename file for file "<file_name>"')
def ui_research_click_rename_file(browser, file_name):
    # Pre condition - only two file rows present  (lorem.txt and SIPI_Jelly_Beans_4.1.07.tiff)
    time.sleep(5)

    found = False
    for file_row_class in ['.even', '.odd']:
        row = browser.find_by_css(file_row_class)[0]
        if not found and row.find_by_css('.sorting_1')[0].value == file_name:
            found = True
            row.find_by_css('.dropdown-toggle')[0].click()
            row.find_by_css('.file-rename').click()
    # file name must be present in browser
    assert found


@when('user renames file to "<new_file_name>"')
def ui_research_rename_file(browser, new_file_name):
    time.sleep(2)
    browser.find_by_id('file-rename-name').fill(new_file_name)
    browser.find_by_css('.btn-confirm-file-rename').click()


@when('new file name "<new_file_name>" is present in folder')
def ui_research_new_file_name_is_present(browser, new_file_name):
    found = False
    time.sleep(10)
    for file_row_class in ['.even', '.odd']:
        row = browser.find_by_css(file_row_class)[0]
        if row.find_by_css('.sorting_1')[0].value == new_file_name:
            found = True
            break
    # renamed file must be present in file browser
    assert found


@when('user browses to subfolder "<subfolder>"')
def ui_browse_subfolder(browser, subfolder):
    time.sleep(5)
    browser.links.find_by_partial_text(subfolder).click()
    time.sleep(10)


# Copied functions
@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    time.sleep(5)
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
