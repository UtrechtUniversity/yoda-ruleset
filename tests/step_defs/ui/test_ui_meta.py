# coding=utf-8
"""Meta UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_meta.feature')


@when('user opens metadata form')
def ui_metadata_open(browser):
    browser.find_by_css('button.metadata-form').click()


@when('users fills in metadata form')
def ui_metadata_fill(browser):
    for input in browser.find_by_css('input.is-invalid'):
        if input.visible:
            browser.driver.execute_script("document.getElementById(arguments[0]).scrollIntoView();", input["id"])
			# Leaving out the sleep the scrolling into view does not work and 'uniteractable element' messages occur
            time.sleep(1)
            input.fill('The quick brown fox jumps over the lazy dog')


@when('users checks person identifier field in metadata form')
def ui_metadata_check_person_id_field(browser):
    # Find the fieldset for the first 'Person identifier'
    fieldset = browser.find_by_text('Person identifier')[0].find_by_xpath('..')

    # Find the PersonIdentifier scheme selectbox and open the list
    fieldset.find_by_css('.select-box').click()

    # Click ORCID for a PI scheme
    fieldset.find_by_text('ORCID').click()

    lookup_link = browser.links.find_by_partial_text('Lookup ORCID')
    assert len(lookup_link) > 0
    assert lookup_link[0]['href'] == 'https://orcid.org/orcid-search/search?searchQuery='

	# ORCID brings a specific pattern with it
    # Pattern test
    parent = lookup_link.find_by_xpath('..')

    assert parent.find_by_css('.form-control')[0]['placeholder'] == 'https://orcid.org/0009-0005-4692-1299'
    # Enter own orcid
    orcid = '1234-5678-1234-5678'
    parent.find_by_css('.form-control')[0].fill(orcid.replace('-',''))
    assert parent.find_by_css('.form-control')[0].value == 'https://orcid.org/' + orcid

    ## Now handle SCOPUS
    fieldset.find_by_css('.select-box').click()

    fieldset.find_by_text('Author identifier (Scopus)').click()

    lookup_link = browser.links.find_by_partial_text('Lookup Scopus Author Identifier')
    assert len(lookup_link) > 0
    assert lookup_link[0]['href'] == 'https://www.scopus.com/freelookup/form/author.uri?zone=TopNavBar&origin='

    parent = lookup_link.find_by_xpath('..')

    scopus_id = 'scopus123'
    parent.find_by_css('.form-control')[0].fill(scopus_id)
    assert parent.find_by_css('.form-control')[0]['value'] == scopus_id


@when('users clicks save button')
def ui_metadata_save(browser):
    # Sleep required as it didn't work otherwise
    time.sleep(1)
    browser.find_by_css('.yodaButtons .btn-primary').click()


@when('users clicks delete all metadata button')
def ui_metadata_delete(browser):
    browser.find_by_css('.yodaButtons .btn-danger').click()
	# Sleep required as it didn't work otherwise
    time.sleep(1)
    browser.find_by_css('.confirm').click()


@then('metadata form is saved as yoda-metadata.json')
def ui_metadata_saved(browser):
    assert browser.is_text_present("Updated metadata of folder </research-initial>")


@then('metadata is deleted from folder')
def ui_metadata_deleted(browser):
    browser.is_text_present("Deleted metadata of folder </research-initial>", wait_time=3)
