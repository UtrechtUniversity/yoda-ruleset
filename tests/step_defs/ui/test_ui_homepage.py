# coding=utf-8
"""Homepage tests"""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    scenarios,
    then,
)

scenarios('../../features/ui/ui_homepage.feature')


@then('username "<user>" is shown')
def ui_username_is_shown(browser, user):
    assert browser.is_text_present("You are logged in as {}".format(user))
