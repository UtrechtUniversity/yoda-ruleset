# coding=utf-8
"""Vault UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_vault.feature')


@when('user browses to data package in "<vault>"')
def ui_browse_data_package(browser, vault):
    link = []
    while len(link) == 0:
        link = browser.links.find_by_partial_text(vault)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()

    browser.find_by_css('.sorting_asc').click()

    research = vault.replace("vault-", "research-")
    data_packages = browser.links.find_by_partial_text(research)
    data_packages.click()


@when('user submits the data package for publication')
def ui_data_package_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit-for-publication').click()

    browser.find_by_id('checkbox-confirm-conditions').check()
    browser.find_by_css('.action-confirm-submit-for-publication').click()


@when('user cancels publication of the data package')
def ui_data_package_cancel(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-cancel-publication').click()


@when('user approves the data package for publication')
def ui_data_package_approve(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-approve-for-publication').click()


@when('user requests depublication of data package')
def ui_data_package_depublish(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-depublish-publication').click()
    browser.find_by_css('.action-confirm-depublish-publication').click()


@when('user requests republication of data package')
def ui_data_package_republish(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-republish-publication').click()
    # And confirm republication
    browser.find_by_css('.action-confirm-republish-publication').click()


@then(parsers.parse('the data package status is "{status}"'))
def ui_data_package_status(browser, status):
    for _i in range(25):
        if browser.is_text_present(status, wait_time=3):
            return True
        browser.reload()

    raise AssertionError()


@when('user clicks metatadata button')
def ui_data_package_click_metadata_button(browser):
    browser.find_by_css('button.metadata-form').click()


@then('metadata form is visible')
def ui_data_package_metadata_form_is_visible(browser):
    assert browser.is_element_visible_by_css('.metadata-form', wait_time=5)


@when('user clicks system metadata icon')
def ui_data_package_click_system_metadata_icon(browser):
    browser.is_element_visible_by_css('.system-metadata', wait_time=5)
    browser.find_by_css('.system-metadata-icon').click()


@then('system metadata is visible')
def ui_data_package_system_metadata_is_visible(browser):
    assert browser.is_element_visible_by_css('.system-metadata')


@when('user clicks provenance icon')
def ui_data_package_click_provenance_icon(browser):
    browser.is_element_visible_by_css('.actionlog-icon', wait_time=5)
    browser.find_by_css('.actionlog-icon').click()


@then('provenance information is visible')
def ui_data_package_provenance_information_is_visible(browser):
    assert browser.is_element_visible_by_css('.actionlog')


@when('user clicks action menu to revoke access')
def ui_data_package_revoke_vault_access(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-revoke-vault-access').click()


@then('action menu holds option to grant access to research group')
def ui_data_package_grant_option_present(browser):
    browser.find_by_id('actionMenu').click()
    assert browser.is_element_present_by_css('.action-grant-vault-access')


@when('clicks action menu to grant access')
def ui_data_package_grant_vault_access(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-grant-vault-access').click()


@then('action menu holds option to revoke access from research group')
def ui_data_package_revoke_option_present(browser):
    browser.find_by_id('actionMenu').click()
    assert browser.is_element_present_by_css('.action-revoke-vault-access')


@when('user clicks action menu to copy data package to research')
def ui_data_package_copy_to_resarch(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-copy-vault-package-to-research').click()


@when('user chooses research folder corresponding to "<vault>"')
def ui_browse_research_to_copy_data_package_to(browser, vault):
    research = vault.replace("vault-", "research-")
    href = "?dir=%2F{}".format(research)
    link = []
    while len(link) == 0:
        link = browser.links.find_by_href(href)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('folder-select-browser_next').click()


@when('user presses copy package button')
def ui_user_presses_copy_package_button(browser):
    browser.find_by_id('btn-copy-package').click()


@then('data package is copied to research area')
def ui_data_package_is_copied_to_research(browser):
    browser.find_by_id('actionMenu').click()
    browser.is_element_present_by_css('.action-revoke-vault-access')


@when('user clicks clicks action menu to check compliancy')
def ui_data_package_check_compliancy(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-check-for-unpreservable-files').click()


@when('user chooses policy')
def ui_data_package_choose_policy(browser):
    browser.find_by_id('file-formats-list').click()
    browser.find_option_by_value('DANS').click()


@then('compliancy result is presented')
def ui_data_package_compliancy_is_presented(browser):
    assert browser.find_by_css('p.help')


@when('user clicks action menu go to research')
def ui_data_package_go_to_research(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-go-to-research').click()


@then('the research space of "<vault>" is shown')
def ui_vault_research_space(browser, vault):
    research = vault.replace("vault-", "research-")
    assert browser.is_text_present(research, wait_time=3)
