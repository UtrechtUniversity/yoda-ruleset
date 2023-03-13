# coding=utf-8
"""Settings UI feature tests."""

__copyright__ = 'Copyright (c) 2021-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_settings.feature')


@when(parsers.parse("user sets mail notifications to {type}"))
def ui_settings_check_mail_notifications(browser, type):
    browser.find_by_css('#mail_notifications').click()
    browser.find_by_value(type).click()


@when(parsers.parse("user sets number of items to {type}"))
def ui_settings_check_number_of_items(browser, type):
    browser.find_by_css('#number_of_items').click()
    browser.find_by_value(type).click()


@when('clicks the save button')
def ui_settings_click_save_button(browser):
    browser.find_by_value("Save").click()


@then(parsers.parse("mail notifications is set to {type}"))
def ui_settings_mail_notifications_checked(browser, type):
    assert browser.find_by_css('#mail_notifications').value == type


@then(parsers.parse("number of items is set to {type}"))
def ui_settings_number_of_items_checked(browser, type):
    assert browser.find_by_css('#number_of_items').value == type
