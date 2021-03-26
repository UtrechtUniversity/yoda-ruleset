# coding=utf-8
"""Login OIDC UI feature tests."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from pytest_bdd import (
    given,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_login_redirect.feature')

restricted_page = "{}/group".format(portal_url)

@given('homepage is shown')
def ui_homepage():
    browser.is_text_present("Welcome to Yoda!")


@given('login page is shown')
def ui_login(browser):
    browser.is_text_present("Login to Yoda")


@when('the user navigates to a restricted page')
def ui_login_visit_groupmngr(browser):
    browser.visit(restricted_page)


@when('user "<user>" logs in after being redirected')
def ui_login_directly(browser, user):
    assert "{}/user/login".format(portal_url) in browser.url

    # Fill in username
    browser.find_by_id('f-login-username').fill(user)

    # Fill in password
    browser.find_by_id('f-login-password').fill(password)

    # Find and click the 'Sign in' button
    browser.find_by_id('f-login-submit').click()


@when('user clicks login with OIDC')
def ui_login_oidc(browser):
    # Find and click the 'OIDC Sign in' button
    browser.find_by_css('.btn-secondary').click()


@then('the user is redirected to the login page')
def ui_login_assert_login_page(browser):
    assert browser.url == "{}/user/login".format(portal_url)

@then('the user is redirected to "<page>"')
def ui_user_redirected(browser, page)
    target = ''

    if page == 'homepage':
        target = portal_url
    elif page == 'groupmanager':
        target = "{}/group".format(portal_url)    

    assert browser.url == target

@then('the user is redirected to the original restricted page')
def ui_redirected_after_login(browser):
    assert browser.url == restricted_page
