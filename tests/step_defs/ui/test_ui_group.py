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
    if not browser.is_element_present_by_css('a.list-group-item.active[data-name={}]'.format(group), wait_time=3):
        browser.find_by_css('a.list-group-item[data-name={}]'.format(group), wait_time=3).click()


@when(parsers.parse("user adds {user_add} to group"))
def ui_group_user_add(browser, user_add):
    browser.find_by_css('div#s2id_f-user-create-name').click()
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


@when("user opens group search dialog")
def ui_group_click_group_search_dlg_button(browser):
    browser.find_by_css('.user-search-groups').click()


@when(parsers.parse("searches for groups of user {user_search}"))
def ui_group_fill_in_user_for_groups(browser, user_search):
    browser.find_by_id('input-user-search-groups').fill(user_search)
    browser.find_by_css('.btn-user-search-groups').click()


@then("a list of groups is shown in the dialog")
def ui_group_list_of_groups_for_user_is_shown(browser):
    assert len(browser.find_by_css('.user-search-result-group')) > 0


@when("user clicks first found group")
def ui_group_click_first_item_in_group(browser):
    group_clicked = browser.find_by_css('.user-search-result-group')[0].value
    browser.find_by_css('.user-search-result-group')[0].click()

    group_properties_type = browser.find_by_id('inputGroupPrepend').value
    group_properties_name = browser.find_by_id('f-group-update-name').value
    # Make sure that row clicked has been set in the group manager as the group to be managed
    assert group_clicked == group_properties_type + group_properties_name
