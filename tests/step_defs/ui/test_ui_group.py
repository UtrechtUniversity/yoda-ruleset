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
import time

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




@when("user opens group import dialog")
def ui_group_click_group_import_dlg_button(browser):
    browser.find_by_css('.import-groups-csv').click()


@when("user clicks upload button")
def ui_group_click_upload_button(browser):
    browser.find_by_css('.csv-import-file')[0].fill("C:\\temp\\csv-import-test.csv")

    # File contains 4 groups - check the number of rows presented
    assert len(browser.find_by_css('.import-groupname')) == 4


@when("user clicks allow updates checkbox")
def ui_group_click_cb_allow_updates(browser):
    browser.find_by_id('import-allow-updates').click()
     

@when("user clicks allow deletions checkbox")
def ui_group_click_cb_allow_deletions(browser):
    browser.find_by_id('import-delete-users').click()


@then("process csv")
def ui_group_process_csv(browser):
    browser.find_by_css('.process-csv').click()
    time.sleep(5)
	
    # Check whether 4 checkmarks are present so each row was processed
    assert len(browser.find_by_css('.import-groupname-done')) == 4

    # Check whether each row was processed correctly
    assert len(browser.find_by_css('.import-csv-group-ok')) == 4

    # find first row and click on it.
    elem = browser.find_by_css('.import-csv-group-ok')[0]
    groupname = elem['groupname']
    # assert groupname == '2'
    assert browser.is_element_visible_by_css('.import-csv-group-ok') == True
    # ActionChains(browser).move_to_element(elem).click(elem).perform()

    browser.find_by_css('.import-csv-group-ok').click()
    time.sleep(2)

    assert browser.find_by_id('group-properties-group-name') == '[research-' + groupname + ']'
    time.sleep(5)	

# ActionChains(driver).move_to_element(button).click(button).perform()
	
# import-groupname import-groupname-done import-csv-group-ok
# elem[0]['groupname']

#group-properties-group-name


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
