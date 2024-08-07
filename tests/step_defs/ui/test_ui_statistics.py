# coding=utf-8
"""Statistics UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time
from pathlib import Path

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_statistics.feature')


@when('groupdetails contains initial text')
def ui_statistics_group_details_initial_state(browser):
    assert browser.is_text_present("Please select a group", wait_time=1)


@when(parsers.parse("user views statistics of group {group}"))
def ui_statistics_group_view(browser, group):
    time.sleep(1)
    next_page = True
    while next_page:
        # Next page available, button is not disabled.
        next_page = len(browser.find_by_css('#group-browser_next.disabled')) == 0
        items = browser.find_by_css('#group-browser tr')
        for item in items:
            if item.value.find(group) > -1:
                item.find_by_css('.list-group-item[data-name={}]'.format(group)).click()
                return True
        else:
            # Group not found, try next page.
            browser.find_by_id('group-browser_next').click()
    assert False


@when('export statistics button is clicked')
def ui_statistics_export(browser):
    # For now prevent downloading on windows platforn
    if os.name == "nt":
        return
    # Only click when not in Windows
    browser.find_by_css('a.btn.btn-primary.btn-sm').click()


@then('statistics graph is shown')
def ui_statistics_graph_shown(browser):
    assert browser.is_text_not_present("No storage information found.", wait_time=1)


@then(parsers.parse("storage for {categories} is shown"))
def ui_statistics_category_storage(browser, categories):
    storage_table_rows = browser.find_by_css('.storage-table tbody tr')
    found = False
    for category in categories.split(','):
        found = False
        for row in storage_table_rows:
            if row.value.find(category) >= 0:
                found = True
                break
        if not found:
            # Assert this way so we make visible which category was not found
            assert category == 'Could not find category'

    assert found


@then('csv file is downloaded')
def ui_statistics_csv_downloaded(browser, tmpdir):
    # Short cut for windows environment to prevent testing for actual downloaded files.
    # This as a dialog prevents forced downloading but a choice is requested.
    # Either choose top open with Excel or download.
    # This choice cannot be automated
    # Therefore, skip this test
    if os.name == "nt":
        assert True
        return

    # Below code is correct in itself and therefore left here in full
    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if str(child)[-10:] == "export.csv":
            os.remove(child)
            assert True
            return

    raise AssertionError()
