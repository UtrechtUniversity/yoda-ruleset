# coding=utf-8
"""Group UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import pytest
import splinter
from pytest_bdd import (
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_group.feature')


@when('user has access to group "<group>" in category "<category>"')
def ui_group_access(browser, category, group):
    if not browser.is_element_present_by_css('a.list-group-item.active[data-name={}]'.format(group), wait_time=1):
        browser.find_by_css('div.list-group-item[data-name={}]'.format(category)).click()
        browser.find_by_css('a.list-group-item[data-name={}]'.format(group)).click()


@when('user adds "<user_add>" to group')
def ui_group_user_add(browser, user_add):
    browser.find_by_css('a.user-create-text').click()
    browser.find_by_xpath('//*[@id="s2id_autogen5_search"]').fill(user_add)
    browser.find_by_css('.select2-results .select2-highlighted').click()
    browser.find_by_css('#f-user-create-submit').click()


@when('user promotes "<user_promote>" to group manager')
def ui_group_user_promote(browser, user_promote):
    browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    browser.find_by_css('a.promote-button').click()


@when('user demotes "<user_demote>" to viewer')
def ui_group_user_demote(browser, user_demote):
    browser.find_by_id('user-list').links.find_by_partial_text(user_demote).click()
    browser.find_by_css('a.demote-button').click()


@when('user removes "<user_remove>" from group')
def ui_group_user_remove(browser, user_remove):
    browser.find_by_id('user-list').links.find_by_partial_text(user_remove).click()
    browser.find_by_css('.users a.delete-button').click()
    browser.find_by_css('#f-user-delete.confirm').click()


@then('user "<user_add>" is added to the group')
def ui_group_user_added(browser, user_add):
    assert browser.find_by_css('.users .active').value == user_add


@then('user "<user_remove>" is removed from the group')
def ui_group_user_removed(browser, user_remove):
    with pytest.raises(splinter.exceptions.ElementDoesNotExist):
        browser.is_text_not_present(user_remove, wait_time=1)
        browser.find_by_id('user-list').links.find_by_partial_text(user_remove).value
