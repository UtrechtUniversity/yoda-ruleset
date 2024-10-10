# coding=utf-8
"""Admin UI feature tests."""

__copyright__ = "Copyright (c) 2024, Utrecht University"
__license__ = "GPLv3, see LICENSE"

import os
import time

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    then,
    when,
)

from conftest import portal_url

scenarios("../../features/ui/ui_admin.feature")


@when("the user navigates to the home page")
def ui_admin_navigates_to_home(browser):
    url = "{}/".format(portal_url)
    browser.visit(url)


@then("the text Administration is shown")
def ui_admin_administration_present(browser):
    h1_tags = browser.find_by_tag("h1")  # Avoid finding the one in dropdown
    found = any("administration" in h1.text.lower() for h1 in h1_tags)
    assert found


@then("the Administration option is available in the menu dropdown")
def ui_admin_administration_dropdown_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    found = browser.is_element_present_by_xpath(xpath)
    assert found


@then("the Maintenance Banner feature is visible")
def ui_admin_banner_option_present(browser):
    assert browser.is_text_present("Maintenance Banner")
    assert browser.find_by_id("admin-banner-message").visible
    assert browser.find_by_id("admin-banner-importance").visible
    assert browser.find_by_css("button[id='admin-set-banner']").visible
    assert browser.find_by_css("button[id='admin-remove-banner']").visible


@then("the Portal Theme feature is visible")
def ui_admin_theme_option_present(browser):
    assert browser.is_text_present("Portal Theme")
    assert browser.find_by_id("admin-theme-selection").visible


@then("the Publication Terms feature is visible")
def ui_admin_pub_terms_option_present(browser):
    assert browser.is_text_present("Publication Terms")
    assert browser.find_by_id("admin-publication-terms").visible


@then("the text Access forbidden is shown")
def ui_admin_access_forbidden_present(browser):
    assert browser.is_text_present("Access forbidden")


@then("the Administration option is not available in the menu dropdown")
def ui_admin_administration_dropdown_not_present(browser):
    xpath = "//a[@class='dropdown-item' and @href='/admin/']"
    not_found = browser.is_element_not_present_by_xpath(xpath)
    assert not_found


@when(parsers.parse("the user inputs banner message {message}"))
def ui_admin_inputs_banner_msg(browser, message):
    browser.fill("banner", message)


@when(parsers.parse("the user {action} the checkbox to mark the banner as important"))
def ui_admin_controls_importance(browser, action):
    if action == "checks":
        browser.check("importance")
    elif action == "unchecks":
        browser.uncheck("importance")
    else:
        raise ValueError("Unsupported action.")


@when("the user clicks the Set Banner button")
def ui_admin_clicks_set_banner(browser):
    browser.find_by_id("admin-set-banner").first.click()


@given(parsers.parse("the banner displays the message {message}"))
@then(parsers.parse("the banner displays the message {message}"))
def ui_admin_displays_banner(browser, message):
    assert browser.is_element_present_by_name('banner head')
    assert browser.is_text_present(message)


@then(parsers.parse("the banner background color is {color}"))
def ui_admin_display_banner_color(browser, color):
    element = browser.find_by_css('div.non-production[role="alert"]').first
    is_color_present = color in element['class'].split()
    assert is_color_present


@when("the user clicks the Remove Banner button")
def ui_admin_clicks_remove_banner(browser):
    browser.find_by_id("admin-remove-banner").first.click()


@then("the banner does not exist")
def ui_admin_remove_banner(browser):
    assert browser.is_element_not_present_by_name('banner head')


@when(parsers.parse("the user changes the portal theme to {theme}"))
def ui_admin_changes_theme(browser, theme):
    browser.find_by_id("admin-theme-selection").first.select(theme)


@when("the user clicks the Set Theme button")
def ui_admin_clicks_set_theme(browser):
    browser.find_by_id("admin-set-theme").first.click()


@then(parsers.parse("the new theme displays {host_name}"))
def ui_admin_display_new_theme(browser, host_name):
    assert browser.is_text_present(host_name)


@when(parsers.parse("the user adds text {text} to publication terms"))
def ui_admin_edits_terms(browser, text):
    browser.execute_script("document.getElementById('admin-create-preview').scrollIntoView();")
    time.sleep(1)
    terms = browser.find_by_id('admin-publication-terms').first.value
    browser.fill("publicationTerms", text + terms)


@when("the user clicks the Preview Terms button")
def ui_admin_clicks_preview(browser):
    browser.find_by_id('admin-create-preview').first.click()


@then(parsers.parse("the added text {text} is shown in the preview window"))
def ui_admin_displays_terms_in_preview(browser, text):
    previewed_terms = browser.find_by_css('div[class="modal-body"]').first.value
    assert text in previewed_terms


@when("the user clicks the Set Terms button")
def ui_admin_clicks_set_terms(browser):
    browser.find_by_id('admin-set-terms').first.click()


@when("the user reloads the page")
def ui_admin_reloads(browser):
    browser.reload()


@when(parsers.parse("the text {text} is displayed in the publication terms textarea"))
@then(parsers.parse("the text {text} is displayed in the publication terms textarea"))
def ui_admin_displays_terms(browser, text):
    browser.execute_script("document.getElementById('admin-create-preview').scrollIntoView();")
    time.sleep(1)
    terms = browser.find_by_id('admin-publication-terms').first.value
    assert text in terms


@when(parsers.parse("the user removes the {text} from publication terms"))
def ui_admin_removes_text_from_terms(browser, text):
    terms = browser.find_by_id('admin-publication-terms').first.value
    modified = terms.replace(text, "", 1)
    browser.fill("publicationTerms", modified)


@then(parsers.parse("the text {text} is not displayed in the publication terms textarea"))
def ui_admin_removed_text_not_displayed(browser, text):
    browser.execute_script("document.getElementById('admin-create-preview').scrollIntoView();")
    time.sleep(1)
    terms = browser.find_by_id('admin-publication-terms').first.value
    assert text not in terms


@when(parsers.parse('the user clicks the Upload file format list {filename}'))
def ui_admin_clicks_upload_file_format_button(browser, filename):
    browser.execute_script("document.getElementById('upload-button').scrollIntoView();")
    browser.find_by_css("#upload-button")

    cwd = os.getcwd()
    if os.name == 'nt':
        browser.find_by_css('input[type="file"]')[0].fill("{}\\files\\file_formats\\{}".format(cwd, filename))
    else:
        browser.find_by_css('input[type="file"]')[0].fill("{}/files/file_formats/{}".format(cwd, filename))


@then(parsers.parse('the success message of uploading a file format list {filename} is shown'))
def ui_admin_upload_file_format_success(browser, filename):
    assert browser.is_text_present(f"File format list '{filename}' uploaded successfully.")


@when(parsers.parse('the user selects the file format list {filename} to delete'))
def ui_admin_select_file_format(browser, filename):
    browser.execute_script("document.getElementById('file-formats-list').scrollIntoView();")
    browser.find_by_css('#file-formats-list').click()
    options = browser.find_by_css('#file-formats-list option')
    for option in options:
        if option.value == filename.split('.')[0]:
            option.click()
            break


@when('the user clicks the Delete file format list button')
def ui_admin_click_delete_button(browser):
    browser.find_by_css("#delete-format-button").click()


@then(parsers.parse('the success message for deleting the file format list {filename} is shown'))
def ui_admin_delete_file_format_success(browser, filename):
    assert browser.is_text_present(f"File format list '{filename}' deleted successfully.")
