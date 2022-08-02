# coding=utf-8
"""Group UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import pytest
import splinter
from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_group.feature')


@when(parsers.parse("user has access to group {group} in category {category}"))
def ui_group_access(browser, category, group):
    if not browser.is_element_present_by_css('a.list-group-item.active[data-name={}]'.format(group), wait_time=1):
        browser.find_by_css('div.list-group-item[data-name={}]'.format(category)).click()
        browser.find_by_css('a.list-group-item[data-name={}]'.format(group)).click()


@when(parsers.parse("user adds {user_add} to group"))
def ui_group_user_add(browser, user_add):
    browser.find_by_css('a.user-create-text').click()
    browser.find_by_xpath('//*[@id="s2id_autogen5_search"]').fill(user_add)
    browser.find_by_css('.select2-results .select2-highlighted').click()
    browser.find_by_css('#f-user-create-submit').click()


@when(parsers.parse("user promotes {user_promote} to group manager"))
def ui_group_user_promote(browser, user_promote):
    browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    browser.find_by_css('a.promote-button').click()


@when(parsers.parse("user demotes {user_demote} to viewer"))
def ui_group_user_demote(browser, user_demote):
    browser.find_by_id('user-list').links.find_by_partial_text(user_demote).click()
    browser.find_by_css('a.demote-button').click()


@when(parsers.parse("user removes {user_remove} from group"))
def ui_group_user_remove(browser, user_remove):
    browser.find_by_id('user-list').links.find_by_partial_text(user_remove).click()
    browser.find_by_css('.users a.delete-button').click()
    browser.find_by_css('#f-user-delete.confirm').click()


@then(parsers.parse("user {user_add} is added to the group"))
def ui_group_user_added(browser, user_add):
    assert browser.find_by_css('.users .active').value == user_add


@then(parsers.parse("user {user_remove} is removed from the group"))
def ui_group_user_removed(browser, user_remove):
    with pytest.raises(splinter.exceptions.ElementDoesNotExist):
        browser.is_text_not_present(user_remove, wait_time=1)
        browser.find_by_id('user-list').links.find_by_partial_text(user_remove).value


@when(parsers.parse("searches for member {member}"))
def ui_group_member_search(browser, member):
    browser.find_by_id('user-list-search').fill(member)


@then(parsers.parse("only member {member} is shown"))
def ui_group_member_filtered(browser, member):
    assert browser.is_text_present(member, wait_time=1)
    assert browser.is_text_not_present("groupmanager", wait_time=1)
    assert browser.is_text_not_present("functionaladminpriv", wait_time=1)


@when(parsers.parse("searches for group {group}"))
def ui_group_search(browser, group):
    browser.find_by_id('group-list-search').fill(group)


@then(parsers.parse("only group {group} is shown"))
def ui_group_filtered(browser, group):
    assert browser.is_text_present(group, wait_time=1)
    assert browser.is_text_not_present("core", wait_time=1)
    assert browser.is_text_not_present("default", wait_time=1)
