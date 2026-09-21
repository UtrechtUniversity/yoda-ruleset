# coding=utf-8

__copyright__ = 'Copyright (c) 2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    scenarios,
    then,
    when
)

scenarios('../../features/ui/ui_datarequest.feature')


@when('user clicks submit data request button')
def ui_datarequest_click_submit_data_request(browser):
    browser.links.find_by_partial_text('Submit data request')[0].click()


@when('user fills in draft data request submission form')
def ui_datarequest_fill_draft_form(browser):
    for input in browser.find_by_css('.metadata-form input'):
        if input.visible:
            if input["type"] == "text":
                browser.driver.execute_script("const element = document.getElementById(arguments[0]); element.scrollIntoView();", input["id"])
                if "email" in input["id"]:
                    input.fill('viewer@yoda.test')
                else:
                    input.fill('The quick brown fox jumps over the lazy dog')

    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    for textarea in browser.find_by_css('.metadata-form textarea'):
        if textarea.visible:
            browser.driver.execute_script("const element = document.getElementById(arguments[0]); element.scrollIntoView();", input["id"])
            textarea.fill('The quick brown fox jumps over the lazy dog')

    browser.find_by_name('yoda_contact_pi_is_contact').first.click()
    browser.find_by_name('yoda_contact_participating_researchers').last.click()
    browser.find_by_name('yoda_datarequest_purpose').last.click()


@when('user clicks on save as draft button')
def ui_datarequest_click_save_as_draft(browser):
    browser.find_by_id('saveButton').click()


@when('user fills in data request submission form', target_fixture="title")
def ui_datarequest_fill_form(browser):
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    title = f"UI test: {timestamp}"

    browser.find_by_id('yoda_datarequest_study_information_title').fill(title)

    return title


@when('user clicks on submit button')
def ui_datarequest_click_submit(browser):
    browser.find_by_id('submitButton').click()
    time.sleep(1)


@then('data request is created')
def ui_datarequest_request_created(browser, title):
    assert browser.is_text_present(title)
