# coding=utf-8
"""Homepage tests"""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    scenarios,
    then,
    # when,
)

from tests.conftest import portal_url

scenarios('../../features/ui/ui_homepage.feature')


@given('user "<user>" is logged in')
def ui_user_loggedin(browser, user):
    browser.is_text_present("{}".format(user))

@given('homepage is shown')
def ui_visits_homepage(browser):
    browser.visit("{}".format(portal_url))

@then('username "<user>" is shown')
def ui_username_is_shown(browser, user):
    assert browser.is_text_present("{}".format(user))


# @when('user clicks homepage')
# def ui_browse_homepage(browser):
#     # Find and click the homepage button
#     browser.find_by_css('.navbar-brand').click()

# @when('the user navigates to "<page>"')
# def ui_visits_homepage(browser, page):
#     browser.visit("{}{}".format(portal_url, page))

# @when('the user navigates to homepage')
# def ui_visits_homepage(browser):
#     browser.visit("{}".format(portal_url))




