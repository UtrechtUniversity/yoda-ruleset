# coding=utf-8
"""Meta UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_meta.feature')


@when('user opens metadata form')
def ui_metadata_open(browser):
    browser.find_by_css('button.metadata-form').click()


@when('user fills in metadata form')
def ui_metadata_fill(browser):
    for input in browser.find_by_css('input.is-invalid'):
        if input.visible:
            browser.driver.execute_script("document.getElementById(arguments[0]).scrollIntoView();", input["id"])
            # Leaving out the sleep the scrolling into view does not work and 'uniteractable element' messages occur
            time.sleep(1)
            input.fill('The quick brown fox jumps over the lazy dog')


@when('users checks person identifier field in metadata form')
def ui_metadata_check_person_id_field(browser):
    # Find the fieldset for the first 'Person identifier'.
    fieldset = browser.find_by_text('Person identifier')[0].find_by_xpath('..')

    # Find the PersonIdentifier scheme selectbox and open the list.
    fieldset.find_by_css('.select-box').click()

    # Check ORCID lookup link.
    lookup_link = browser.links.find_by_partial_text('Lookup ORCID')
    assert len(lookup_link) > 0
    assert lookup_link[0]['href'] == 'https://orcid.org/orcid-search/search?searchQuery='

    parent = lookup_link.find_by_xpath('..')

    # Check ORCID placeholder.
    assert parent.find_by_css('.form-control')[0]['placeholder'] == 'https://orcid.org/0009-0005-4692-1299'

    # Enter ORCID.
    orcid = '0009-0005-4692-1299'
    parent.find_by_css('.form-control')[0].fill(orcid.replace('-', ''))
    assert parent.find_by_css('.form-control')[0].value == 'https://orcid.org/' + orcid

    # Select Author identifier (Scopus).
    fieldset.find_by_css('.select-box').click()
    fieldset.find_by_text('Author identifier (Scopus)').click()

    # Check Author identifier (Scopus) lookup link.
    lookup_link = browser.links.find_by_partial_text('Lookup Author identifier (Scopus)')
    assert len(lookup_link) > 0
    assert lookup_link[0]['href'] == 'https://www.scopus.com/freelookup/form/author.uri?zone=TopNavBar&origin='

    parent = lookup_link.find_by_xpath('..')

    # Check Author identifier (Scopus) placeholder.
    assert parent.find_by_css('.form-control')[0]['placeholder'] == '51161516100'


@when('user clicks save button')
def ui_metadata_save(browser):
    browser.find_by_css('.yodaButtons .btn-primary').click()


@when('users clicks delete all metadata button')
def ui_metadata_delete(browser):
    browser.find_by_css('.yodaButtons .btn-danger').click()
    browser.find_by_css('.confirm').click()


@then(parsers.parse('metadata form is saved as yoda-metadata.json for folder {folder}'))
def ui_metadata_saved(browser, folder):
    assert browser.is_text_present("Updated metadata of folder </{}>".format(folder))


@then('metadata is deleted from folder')
def ui_metadata_deleted(browser):
    browser.is_text_present("Deleted metadata of folder </research-initial>", wait_time=3)


@then('an error is shown that the path does not exist')
def ui_metadata_path_not_exist(browser):
    browser.is_text_present("The given path does not exist", wait_time=3)
