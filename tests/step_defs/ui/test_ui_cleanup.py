# coding=utf-8

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import os
import time
from collections import OrderedDict

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when
)
from selenium.webdriver.common.keys import Keys

from conftest import api_request, upload_data

scenarios('../../features/ui/ui_cleanup.feature')


@given(parsers.parse('"{file}" is uploaded to folder "<folder>"'), target_fixture="api_response")
def api_cleanup_file_upload(user, file, folder):
    return upload_data(
        user,
        '\.' + file,
        "/{}".format(folder)
    )


@then('no temporary files remaining')
def ui_cleanup_rows_none(browser):
    assert len(browser.find_by_css('.cleanup-select-file')) == 0


@then('dialog closed and successfully deleted message showing')
def ui_cleanup_dlg_closed_deletion_success(browser):
    assert browser.find_by_css('.alert-success').value.startswith('Successfully')


@when('confirm deletion of all selected files')
def ui_cleanup_confirm_all_selected_files(browser):
    browser.find_by_css('.btn-confirm-cleanup-collection').click()


@when('check all remaining files')
def ui_cleanup_check_all_remaining_files(browser):
    browser.find_by_css('.cleanup-check-all').click()


@then('successfully deleted and 3 remaining')
def ui_cleanup_rows_three(browser):
    assert len(browser.find_by_css('.cleanup-select-file')) == 3


@when('confirm deletion of file')
def ui_cleanup_deletion_confirm(browser):
    confirm = browser.switch_to.alert
    confirm.accept()


@when('delete first file directly')
def ui_cleanup_delete_first_directly(browser):
    browser.find_by_css('.cleanup-single-file').click()


@when('user opens cleanup dialog')
def ui_cleanup_open_dialog(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-cleanup').click()
