# coding=utf-8
"""Browse UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    parsers,
    scenarios,
    then
)

scenarios('../../features/ui/ui_browse.feature')


@then(parsers.parse("there is no link to {file} in folder {folder}"))
def ui_browse_stay_research_space(browser, file, folder):
    assert len(browser.find_by_css("[data-path='/{}/{}']".format(folder, file))) == 0
