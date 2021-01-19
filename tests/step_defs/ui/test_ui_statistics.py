# coding=utf-8
"""Statistics UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
from pathlib import Path

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_statistics.feature')


@when(parsers.parse('user views statistics of group "{group}"'))
def ui_statistics_group_view(browser, group):
    browser.find_by_css('a.list-group-item[data-name={}]'.format(group)).click()


@when('export statistics button is clicked')
def ui_statistics_export(browser):
    browser.find_by_css('a.btn.btn-primary.btn-sm').click()


@then('statistics graph is shown')
def ui_statistics_graph_shown(browser):
    browser.is_text_not_present("No storage information found.", wait_time=1)


@then('storage for "<storage_type>" is shown')
def ui_statistics_category_storage(browser, storage_type):
    browser.is_text_present(storage_type, wait_time=1)


@then('csv file is downloaded')
def ui_statistics_csv_downloaded(browser, tmpdir):
    root_dir = Path(tmpdir).parent
    download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if str(child)[-4:] == ".csv":
            os.remove(child)
            assert True
        else:
            raise AssertionError()
