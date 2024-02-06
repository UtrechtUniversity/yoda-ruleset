#!/usr/bin/env python3
"""Common UI test functions."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    then,
    when,
)


@given(parsers.parse('text "{text}" is shown'))
@when(parsers.parse('text "{text}" is shown'))
@then(parsers.parse('text "{text}" is shown'))
def ui_text_shown(browser, text):
    assert browser.is_text_present(text)


@when(parsers.parse("user browses to folder {folder}"))
@then(parsers.parse("user browses to folder {folder}"))
def ui_browse_folder(browser, folder):
    link = []
    counter = 0

    while len(link) == 0:
        link = browser.links.find_by_partial_text(folder)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()
            if counter > 6:
                assert False
            counter += 1


@when(parsers.parse("user clicks on file {file} in folder {folder}"))
def ui_browse_file(browser, file, folder):
    browser.find_by_css(f"[data-path='/{folder}/{file}']").click()


@when('user clicks go to group manager')
def ui_go_to_group_manager(browser):
    browser.find_by_css('.btn-go-to-group-manager').click()


@when(parsers.parse("correct row in tree is active for {group}"))
@then(parsers.parse("correct row in tree is active for {group}"))
def ui_group_tree_correct_row_active(browser, group):
    assert browser.find_by_css('a.group.active[data-name={}]'.format(group), wait_time=1)
