# coding=utf-8
"""Browse UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_browse.feature')


@when('user browses to data package "<data_package>"')
def ui_browse_data_package(browser, data_package):
    browser.links.find_by_partial_text(data_package).click()


@then('the 404 error page is shown')
def ui_browse_404(browser):
    browser.is_text_present("Page not found")
