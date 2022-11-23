# coding=utf-8
"""Group UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import time

import pytest
import splinter
from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_group.feature')


@when(parsers.parse("user selects group {group} in subcategory {subcategory} and category {category}"))
def ui_group_subcategory_category_access(browser, category, subcategory, group):
    # First, find if group is present AND active
    if not browser.find_by_css('a.group.active[data-name={}]'.format(group), wait_time=1):
        # Perhaps the group is not present at all.
        if browser.find_by_css('a.group[data-name={}]'.format(group), wait_time=1).visible:
            # If group is present, click it to make it active.
            browser.find_by_id('group-list').links.find_by_partial_text(group).click()
        else:
            # if group is not found, this indicates that at least the subcategory is closed or not even present.
            if browser.find_by_css('div.list-group-item.subcategory[data-name={}] a'.format(subcategory)).visible:
                # category is closed, so first open it.
                browser.find_by_css('div.list-group-item.subcategory[data-name={}] a'.format(subcategory)).click()
                # Click on the group so group gets selected
                browser.find_by_id('group-list').links.find_by_partial_text(group).click()
            else:
                # subcat is not found which can only be the case if the category is closed.
                browser.find_by_css('div.list-group-item.category[data-name={}] a'.format(category), wait_time=1).click()
                # Now open the subcategory
                browser.find_by_css('div.list-group-item.subcategory[data-name={}] a'.format(subcategory)).click()
                # Click on the group so group gets selected
                browser.find_by_id('group-list').links.find_by_partial_text(group).click()


@then(parsers.parse("test if member {member_add} is added to the group"))
def ui_group_user_is_added(browser, member_add):
    assert browser.find_by_id('user-list').links.find_by_partial_text(member_add)


@when(parsers.parse("user adds {member_add} to group"))
def ui_group_user_add(browser, member_add):
    time.sleep(3)
    browser.find_by_css('div#s2id_f-user-create-name').click()
    browser.find_by_xpath('//*[@id="s2id_autogen6_search"]').fill(member_add)
    browser.find_by_css('.select2-results .select2-highlighted').click()
    browser.find_by_css('#f-user-create-submit').click()


@when(parsers.parse("user selects two members {member1} and {member2}"))
def ui_group_select_multiple_users(browser, member1, member2):
    browser.find_by_id('user-list').links.find_by_partial_text(member1).click()
    browser.find_by_id('user-list').links.find_by_partial_text(member2).click()
    # time.sleep(5)


@when(parsers.parse("user changes roles to {new_role}"))
def ui_group_userrole_change(browser, new_role):
    # browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    browser.find_by_css('a.update-button[data-target-role={}]'.format(new_role), wait_time=1).click()


@then("role change is successful")
def ui_group_role_change_success(browser):
    # browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    # browser.find_by_css('a.update-button[data-target-role={}]'.format(new_role), wait_time=1).click()
    assert browser.find_by_text('User roles were updated successfully.')


@when("user removes selected members")
def ui_group_remove_users_from_group(browser):
    # browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    browser.find_by_css('.users .delete-button', wait_time=1).click()


@when('remove members from group is confirmed')
def ui_group_remove_members_confirm(browser):
    browser.find_by_id('f-user-delete').click()
    # time.sleep(5)


@then("members successfully removed")
def ui_group_remove_members_success(browser):
    # browser.find_by_id('user-list').links.find_by_partial_text(user_promote).click()
    # browser.find_by_css('a.update-button[data-target-role={}]'.format(new_role), wait_time=1).click()
    assert browser.find_by_text('Users were removed successfully.')


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


@then("user opens group import dialog")
@when("user opens group import dialog")
def ui_group_click_group_import_dlg_button(browser):
    browser.find_by_css('.import-groups-csv').click()


@when("user clicks upload button")
def ui_group_click_upload_button(browser):
    cwd = os.getcwd()
    if os.name == 'nt':
        browser.find_by_css('.csv-import-file')[0].fill("{}\\files\\csv-import-test.csv".format(cwd))
    else:
        browser.find_by_css('.csv-import-file')[0].fill("{}/files/csv-import-test.csv".format(cwd))

    # File contains 4 groups - check the number of rows presented.
    assert len(browser.find_by_css('.import-groupname')) == 4


@when("user clicks allow updates checkbox")
def ui_group_click_cb_allow_updates(browser):
    browser.find_by_id('import-allow-updates').click()


@when("user clicks allow deletions checkbox")
def ui_group_click_cb_allow_deletions(browser):
    browser.find_by_id('import-delete-users').click()


@when("user clicks remove group")
def ui_group_clicks_remove_group(browser):
    browser.links.find_by_partial_text("Remove group")[0].click()


@when("user confirms group removal")
def ui_group_confirms_group_removal(browser):
    browser.find_by_id('f-group-delete').click()


@then("process csv and check number of rows")
def ui_group_process_csv(browser):
    # Start processing the uploaded file.
    browser.find_by_css('.process-csv').click()

    # Take enough time so processing is complete.
    time.sleep(5)

    # Check whether 4 checkmarks are present so each row was processed.
    assert len(browser.find_by_css('.import-groupname-done')) == 4

    # Check whether each row was processed correctly.
    assert len(browser.find_by_css('.import-csv-group-ok')) == 4


@then(parsers.parse("click on imported row {row} and check group properties"))
def ui_group_csv_click_row(browser, row):
    # Find the indicated row and click on it.
    groupname = browser.find_by_css('.import-csv-group-ok')[int(row)]['groupname']

    # Use the checkmark as that was the only way to circumvent.
    browser.find_by_id("processed-indicator-" + groupname).click()

    assert browser.find_by_id('group-properties-group-name').value == '[research-' + groupname + ']'
    assert browser.find_by_id('f-group-update-name').value == groupname


@then(parsers.parse('find groupmember "{group_member}"'))
def ui_group_csv_find_group_member(browser, group_member):
    # Find the groupmember in the group member list.
    if len(browser.links.find_by_partial_text(group_member)):
        assert True
        return
    assert False


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


@when("user opens add group dialog")
def ui_group_schema_create_group(browser):
    browser.find_by_css('.create-button-new').click()


@when(parsers.parse("groupname is set to {group}"))
def ui_group_schema_set_groupname(browser, group):
    browser.find_by_id('f-group-create-name').fill(group)


@when(parsers.parse("group type is set to datamanager"))
def ui_group_set_group_type(browser):
    browser.find_by_id('f-group-create-prefix-button').click()
    browser.find_by_id('f-group-create-prefix-datamanager').click()


@when(parsers.parse("category is set to {category}"))
def ui_group_schema_category_is_set(browser, category):
    # Category already exists.
    browser.find_by_id('s2id_f-group-create-category').click()
    options = browser.find_by_css('.select2-result')
    for option in options:
        if option.text == category:
            option.click()
            return True

    # Category does not exist.
    browser.find_by_xpath('//*[@id="s2id_autogen1_search"]').fill(category)
    browser.find_by_css('.select2-results .select2-highlighted').click()


@when(parsers.parse("subcategory is set to {subcategory}"))
def ui_group_schema_subcategory_is_set(browser, subcategory):
    # Subcategory already exists.
    browser.find_by_id('s2id_f-group-create-subcategory').click()
    options = browser.find_by_css('.select2-result')
    for option in options:
        if option.text == subcategory:
            option.click()
            return True

    # Subcategory does not exist.
    browser.find_by_xpath('//*[@id="s2id_autogen3_search"]').fill(subcategory)
    browser.find_by_css('.select2-results .select2-highlighted').click()


@when(parsers.parse("schema id is set to {schema_id}"))
def ui_group_schema_set_schema_id(browser, schema_id):
    browser.find_by_id('s2id_f-group-create-schema-id').click()

    options = browser.find_by_css('.select2-result')
    for option in options:
        if option.text == schema_id:
            option.click()
            break


@when("user submits new group data")
def ui_schema_submit_new_group_data(browser):
    browser.find_by_id('f-group-create-submit').click()


@when(parsers.parse("research group {group} is successfully created"))
def ui_group_schema_assert_research_group_created(browser, group):
    assert browser.find_by_css('.alert-success').text == 'Created group research-' + group + '.'


@when(parsers.parse("datamanager group {group} is successfully created"))
def ui_group_schema_assert_datamanager_group_created(browser, group):
    assert browser.find_by_css('.alert-success').text == 'Created group datamanager-' + group + '.'


@when(parsers.parse("check whether research group properties {group}, {category} and {schema_id} are correct"))
def ui_group_schema_properties_schema_correct(browser, group, category, schema_id):
    assert browser.find_by_id('f-group-update-name').value == group
    assert browser.find_by_id('f-group-update-schema-id').value == schema_id
    div = browser.find_by_id('s2id_f-group-update-category')
    assert div.find_by_css('.select2-chosen').text == category


@when(parsers.parse("check whether datamanager group properties {group} and {category} are correct"))
def ui_group_schema_properties_correct(browser, group, category):
    assert browser.find_by_id('f-group-update-name').value == group
    div = browser.find_by_id('s2id_f-group-update-category')
    assert div.find_by_css('.select2-chosen').text == category
