# coding=utf-8

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
    when
)

scenarios('../../features/ui/ui_deposit.feature')


@when('user starts a new deposit')
def ui_deposit_start(browser):
    browser.links.find_by_partial_text('Start new deposit').click()


@when('user clicks on active deposit')
def ui_deposit_click_active(browser):
    browser.links.find_by_partial_text('deposit-pilot[')[0].click()


@when('user clicks on document data button')
def ui_deposit_click_document(browser):
    browser.links.find_by_partial_text('Document data').click()


@then('new deposit is created')
def ui_deposit_created(browser):
    assert browser.is_text_present("deposit-pilot[")


@then('upload data step is shown')
def ui_deposit_upload_data_shown(browser):
    assert browser.is_text_present("Upload data")


@then('document data step is shown')
def ui_deposit_document_data(browser):
    assert browser.is_text_present("Upload data")
