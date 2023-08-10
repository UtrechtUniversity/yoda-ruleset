# coding=utf-8
"""Settings UI feature tests."""

__copyright__ = 'Copyright (c) 2021-2023, Utrecht University'
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


@when(parsers.parse("user sets group manager view to {type}"))
def ui_settings_check_group_manager_view(browser, type):
    browser.find_by_css('#group_manager_view').click()
    browser.find_by_value(type).click()


@when(parsers.parse("user sets color mode to {type}"))
def ui_settings_check_color_mode(browser, type):
    browser.find_by_css('#color_mode').click()
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


@then(parsers.parse("group manager view is set to {type}"))
def ui_settings_group_manager_view_checked(browser, type):
    assert browser.find_by_css('#group_manager_view').value == type


@then(parsers.parse("color mode is set to {type}"))
def ui_settings_color_mode_checked(browser, type):
    assert browser.find_by_css('#color_mode').value == type
