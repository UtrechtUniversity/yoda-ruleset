# coding=utf-8
"""Research UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    parsers,
    scenarios,
    when,
    then,
)

scenarios('../../features/ui/ui_research.feature')

@given('user "<user>" is logged in')
@given(parsers.parse('user "{user}" is logged in'))
def ui_login(browser, user):
    url = "https://portal.yoda.test/user/login"
    browser.visit(url)

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)

    # Fill in password
    browser.find_by_id('f-login-password').fill('test')

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()


@given(parsers.parse('module "{module}" module is shown'))
def ui_module_shown(browser, module):
    url = "https://portal.yoda.test/{}".format(module)
    browser.visit(url)


@when('user browses to folder "<folder>"')
def ui_browse_folder(browser, folder):
    browser.links.find_by_partial_text(folder).click()


@when('user adds a new folder "<folder_new>"')
def ui_research_folder_add(browser, folder_new):
    assert True


@when('user renames folder "<folder_old>" to "<folder_new>"')
def ui_research_folder_rename(browser, folder_old, folder_new):
    assert True


@when('user deletes folder "<folder_delete>"')
def ui_research_folder_delete(browser, folder_delete):
    assert True


@then('folder "<folder_new>" exists in "<folder>"')
def ui_research_folder_exists(browser, folder_new, folder):
    assert True


@then('folder "<folder_delete>" does not exists in "<folder>"')
def ui_research_folder_exists(browser, folder_delete, folder):
    assert True
