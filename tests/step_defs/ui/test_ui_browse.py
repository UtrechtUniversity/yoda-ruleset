# coding=utf-8
"""Browse UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    when,
)

scenarios('../../features/ui/ui_browse.feature')


@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    browser.links.find_by_partial_text(folder).click()


@when('user browses to data package "<data_package>"')
def ui_browse_data_package(browser, data_package):
    browser.links.find_by_partial_text(data_package).click()
