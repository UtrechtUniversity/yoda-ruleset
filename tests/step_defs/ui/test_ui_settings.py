# coding=utf-8
"""Settings UI feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_settings.feature')


@when('user checks mail notifications checkbox')
def ui_settings_check_mail_notifications(browser):
    browser.find_by_css('input#mail_notifications').check()


@when('clicks the save button')
def ui_settings_click_save_button(browser):
    browser.find_by_value("Save").click()


@then('mail notifications checkbox is checked')
def ui_settings_mail_notifications_checked(browser):
    assert browser.find_by_css('input#mail_notifications').value == 'on'
