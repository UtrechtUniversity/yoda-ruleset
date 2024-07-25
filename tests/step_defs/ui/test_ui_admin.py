# coding=utf-8
"""Admin UI feature tests."""

__copyright__ = "Copyright (c) 2024, Utrecht University"
__license__ = "GPLv3, see LICENSE"

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import portal_url

scenarios("../../features/ui/ui_admin.feature")


@given(parsers.parse("the banner display the message {message}"))
@then(parsers.parse("the banner display the message {message}"))
def ui_admin_display_banner(browser, message):
    assert browser.is_element_present_by_name('banner head')
    assert browser.is_text_present(message)


@when("the user navigates to the home page")
def ui_admin_home_access(browser):
    url = "{}/".format(portal_url)
    browser.visit(url)


@when("the user navigates to the admin page")
def ui_admin_access(browser):
    url = "{}/admin".format(portal_url)
    browser.visit(url)


@when(parsers.parse("the user input banner text with message {message}"))
def ui_admin_input_banner_msg(browser, message):
    browser.fill("banner", message)


@when(parsers.parse("the user {action} the checkbox to mark the banner as important"))
def ui_admin_control_importance(browser, action):
    if action == "checks":
        browser.check("importance")
    elif action == "unchecks":
        browser.uncheck("importance")
    else:
        raise ValueError("Unsupported action.")


@when(parsers.parse("the user click button {button}"))
def ui_admin_click_button(browser, button):
    browser.find_by_name(button).first.click()


@when(parsers.parse("the user change portal theme to {theme}"))
def ui_admin_change_theme(browser, theme):
    browser.find_by_id("theme").first.select(theme)


@then("the text Administration is shown")
def ui_admin_administration_present(browser):
    h1_tags = browser.find_by_tag("h1")  # Avoid finding the one in dropdown
    found = any("administration" in h1.text.lower() for h1 in h1_tags)
    assert found


@then("Administration option is available in the menu dropdown")
def ui_admin_administration_dropdown_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    found = browser.is_element_present_by_xpath(xpath)
    assert found


@then("Administration option is not available in the menu dropdown")
def ui_admin_administration_dropdown_not_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    not_found = browser.is_element_not_present_by_xpath(xpath)
    assert not_found


@then("the text Access forbidden is shown")
def ui_admin_access_forbidden(browser):
    assert browser.is_text_present("Access forbidden")


@then("the banner setup option should be visible")
def ui_admin_banner_option_present(browser):
    assert browser.is_text_present("Set Maintenance Banner"), "Banner title not found on the page"
    assert browser.find_by_name("banner").visible, "Textarea for banner message not found on the page"
    assert browser.find_by_id("importance").visible, "Checkbox for 'Mark as Important' not found on the page"
    assert browser.find_by_css("button[name='Set Banner']").visible, "Button to set the banner not found on the page"
    assert browser.find_by_css("button[name='Remove Banner']").visible, "Button to remove the banner not found on the page"


@then("the theme change option should be visible")
def ui_admin_theme_option_present(browser):
    assert browser.is_text_present("Change Portal Theme"), "Change Theme title not found on the page"
    assert browser.find_by_name("theme").visible, "Theme Selection not found on the page"


@then("the banner does not exist")
def ui_admin_remove_banner(browser):
    assert browser.is_element_not_present_by_name('banner head')


@then(parsers.parse("the banner background color should be {color}"))
def ui_admin_display_banner_color(browser, color):
    element = browser.find_by_css('div.non-production[role="alert"]').first
    is_color_present = color in element['class'].split()
    assert is_color_present


@then(parsers.parse("the new theme should display {host_name}"))
def ui_admin_display_new_theme(browser, host_name):
    assert browser.is_text_present(host_name)