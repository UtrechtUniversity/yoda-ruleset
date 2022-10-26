# coding=utf-8
"""Browse UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
)

scenarios('../../features/ui/ui_browse.feature')


@then('the 404 error page is shown')
def ui_browse_404(browser):
    browser.is_text_present("Page not found")
