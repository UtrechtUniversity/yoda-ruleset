# coding=utf-8
"""Group UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
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

from conftest import api_request, roles

scenarios('../../features/ui/ui_group.feature')


@when(parsers.parse("checks group properties for {group}"))
def ui_group_check_properties_panel(browser, group):
    # strip off research partition
    grp = '-'.join(group.split('-')[1:])
    assert browser.find_by_id('group-properties-group-name').value == '[research-' + grp + ']'
    assert browser.find_by_id('f-group-update-name').value == grp

    # Check if creation data is present.
    assert browser.find_by_id('f-group-update-creation-date', wait_time=1).visible


@when(parsers.parse("correct row in list view is active for {group}"))
def ui_group_list_view_correct_row_active(browser, group):
    assert len(browser.find_by_css('#tbl-list-groups tr.active[user-search-result-group="{}"]'.format(group))) == 1


@when(parsers.parse("user selects group {group} in list view"))
def ui_group_list_view_select_group(browser, group):
    table = browser.find_by_id('tbl-list-groups')
    rows = table.find_by_css('tr.user-search-result-group')

    for row in rows:
        group_name = row.find_by_tag('td').first
        if group_name.value == group:
            group_name.click()
            assert True
            return

    raise AssertionError()


@when(parsers.parse("user selects tree view"))
def ui_group_select_group_tree_view(browser):
    browser.find_by_id('pills-tree-tab').click()


@when(parsers.parse("user selects list view"))
def ui_group_select_group_list_view(browser):
    browser.find_by_id('pills-list-tab').click()


@when(parsers.parse("user searches for users {user} in list view"))
def ui_group_list_search_user(browser, user):
    tbl = browser.find_by_id('tbl-list-groups')
    # get unfitlered table group count
    groups_1 = len(tbl.find_by_css('.user-search-result-group'))

    div = browser.find_by_css('.selectify-search').find_by_xpath('..').find_by_css('span .select2-selection')
    div.click()
    time.sleep(4)
    browser.find_by_css('.select2-search__field').fill(user)
    time.sleep(4)
    browser.find_by_css('.select2-results__option--highlighted').click()
    # time.sleep(3)

    groups_2 = len(tbl.find_by_css('.user-search-result-group'))

    assert groups_1 > groups_2


@when(parsers.parse("user searches for groups {group} in list view"))
def ui_group_list_search_group(browser, group):
    tbl = browser.find_by_id('tbl-list-groups')
    # get unfitlered table group count
    groups_1 = len(tbl.find_by_css('.user-search-result-group'))

    browser.find_by_id('search').fill(group)
    # get group count after filtering
    groups_2 = len(tbl.find_by_css('.user-search-result-group'))

    assert groups_1 > groups_2


@when(parsers.parse("user searches for users {user} in tree"))
def ui_group_tree_search_user(browser, user):
    tbl = browser.find_by_id('group-list')
    # get unfitlered table group count
    groups_1 = len(tbl.find_by_css('.list-group-item.group:not(.filtered)'))

    browser.find_by_css('div#s2id_search').click()
    browser.find_by_xpath('//*[@id="s2id_autogen7_search"]').fill(user)
    browser.find_by_css('.select2-results .select2-highlighted').click()

    # get group count after filtering
    groups_2 = len(tbl.find_by_css('.list-group-item.group:not(.filtered)'))

    assert groups_1 > groups_2


@when(parsers.parse("user searches for groups {group} in tree"))
def ui_group_tree_search_group(browser, group):
    tbl = browser.find_by_id('group-list')
    # get unfitlered table group count
    groups_1 = len(tbl.find_by_css('.list-group-item.group:not(.filtered)'))

    browser.find_by_id('search').fill(group)

    # get group count after filtering
    groups_2 = len(tbl.find_by_css('.list-group-item.group:not(.filtered)'))

    assert groups_1 > groups_2


@when(parsers.parse("user enters search argument {search}"))
def ui_group_tree_search_user_argument(browser, search):
    browser.find_by_css('.selectify-search').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(2)
    browser.find_by_css('.select2-search__field').fill(search)
    time.sleep(2)


@when(parsers.parse("autocomplete returns {suggestions} suggestions"))
def ui_group_count_user_search_result(browser, suggestions):
    users = browser.find_by_css('.select2-results__option')
    assert len(users) == (int(suggestions) + 1)


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
    browser.find_by_css('#f-user-create-name').find_by_xpath('..').find_by_css('span .select2-selection').click()
    # Scroll to bottom.
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    browser.find_by_css('.select2-search__field').fill(member_add)
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    browser.find_by_css('.select2-results__option--highlighted').click()
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    browser.find_by_css('#f-user-create-submit').click()


@when(parsers.parse("user selects two members {member1} and {member2}"))
def ui_group_select_multiple_users(browser, member1, member2):
    browser.find_by_id('user-list').links.find_by_partial_text(member1).click()
    browser.find_by_id('user-list').links.find_by_partial_text(member2).click()


@when(parsers.parse("user changes roles to {new_role}"))
def ui_group_userrole_change(browser, new_role):
    browser.find_by_css('a.update-button[data-target-role={}]'.format(new_role), wait_time=1).click()


@then("role change is successful")
def ui_group_role_change_success(browser):
    assert browser.find_by_text('User roles were updated successfully.')


@when("user removes selected members")
def ui_group_remove_users_from_group(browser):
    browser.find_by_css('.users .delete-button', wait_time=1).click()


@when('remove members from group is confirmed')
def ui_group_remove_members_confirm(browser):
    browser.find_by_id('f-user-delete').click()


@then("members successfully removed")
def ui_group_remove_members_success(browser):
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
    # Scroll to bottom.
    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    browser.find_by_id('user-list-search').fill(member)   # rechterkant search member


@then(parsers.parse("only member {member} is shown"))
def ui_group_member_filtered(browser, member):
    assert browser.is_text_present(member, wait_time=1)
    user_list = browser.find_by_css("#user-list a")
    for user in user_list:
        if 'datamanager' in user['data-name']:
            assert not user.visible
        if 'functionaladminpriv' in user['data-name']:
            assert not user.visible


@when(parsers.parse("searches for group {group}"))
def ui_group_search(browser, group):
    browser.find_by_css('.selectify-search').find_by_xpath('..').find_by_css('span .select2-selection').click()
    browser.find_by_css('.select2-search__field').fill(group)
    browser.find_by_css('.select2-results__option--highlighted').click()


@then(parsers.parse("only group {group} is shown"))
def ui_group_filtered(browser, group):
    assert browser.is_text_present(group, wait_time=1)

    core_groups = browser.find_by_css("a[data-name*=\"{}\"]".format("core"))
    for grp in core_groups:
        assert not grp.visible

    default_groups = browser.find_by_css("a[data-name*=\"{}\"]".format("default"))
    for grp in default_groups:
        assert not grp.visible


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


@then(parsers.parse('find group member "{group_member}"'))
def ui_group_csv_find_group_member(browser, group_member):
    # Find the groupmember in the group member list.
    if len(browser.links.find_by_partial_text(group_member)):
        assert True
        return
    assert False


@when(parsers.parse("searches for groups of user {user_search}"))
def ui_group_fill_in_user_for_groups(browser, user_search):
    browser.find_by_id('input-user-search-groups').fill(roles[user_search]["username"])
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


@when("user clicks group properties header")
def ui_group_click_group_properties_header(browser):
    browser.find_by_css('#properties-update-link').first.click()


@then("group properties is collapsed")
def ui_group_group_properties_collapsed(browser):
    group_properties = browser.find_by_css('#group-properties')

    # Make sure that card is collapsed
    assert not group_properties.first.visible


@then("group properties is not collapsed")
def ui_group_group_properties_not_collapsed(browser):
    group_properties = browser.find_by_css('#group-properties')

    # Make sure that card is not collapsed
    assert group_properties.first.visible


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
    browser.find_by_css('#f-group-create-category').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(1)
    options = browser.find_by_css('#select2-f-group-create-category-results')
    for option in options:
        if option.text == category:
            option.click()
            return True

    # Category does not exist.
    time.sleep(1)
    browser.find_by_css('.select2-search__field').fill(category)
    time.sleep(1)
    browser.find_by_css('.select2-results__option--highlighted').click()


@when(parsers.parse("category is updated to {category}"))
def ui_group_schema_category_is_updated(browser, category):
    # Category already exists.
    browser.find_by_css('#f-group-update-category').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(1)
    options = browser.find_by_css('#select2-f-group-update-category-results')
    for option in options:
        if option.text == category:
            option.click()
            return True

    # Category does not exist.
    time.sleep(1)
    browser.find_by_css('.select2-search__field').fill(category)
    time.sleep(1)
    browser.find_by_css('.select2-results__option--highlighted').click()


@when(parsers.parse("subcategory is set to {subcategory}"))
def ui_group_schema_subcategory_is_set(browser, subcategory):
    browser.find_by_css('#f-group-create-subcategory').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(1)
    browser.find_by_css('.select2-search__field').fill(subcategory)
    time.sleep(1)
    options = browser.find_by_css('#select2-f-group-create-subcategory-results')
    for option in options:
        if subcategory in option.text:
            option.click()
            return True


@when(parsers.parse("subcategory is updated to {subcategory}"))
def ui_group_schema_subcategory_is_updated(browser, subcategory):
    browser.find_by_css('#f-group-update-subcategory').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(1)
    browser.find_by_css('.select2-search__field').fill(subcategory)
    time.sleep(1)
    options = browser.find_by_css('#select2-f-group-update-subcategory-results')
    for option in options:
        if subcategory in option.text:
            option.click()
            return True


@when(parsers.parse("schema id is set to {schema_id}"))
def ui_group_schema_set_schema_id(browser, schema_id):
    browser.find_by_css('#f-group-create-schema-id').find_by_xpath('..').find_by_css('span .select2-selection').click()
    time.sleep(4)
    options = browser.find_by_css('.select2-results__options')
    for option in options:
        if option.text == schema_id:
            option.click()
            break


@when(parsers.parse("expiration date is set to {expiration_date}"))
def ui_group_schema_set_expiration_date(browser, expiration_date):
    browser.find_by_id('f-group-create-expiration-date').fill(expiration_date)


@when(parsers.parse("expiration date is updated to {expiration_date}"))
def ui_group_schema_update_expiration_date(browser, expiration_date):
    browser.find_by_id('f-group-update-expiration-date').fill(expiration_date)


@when("user submits new group data")
def ui_schema_submit_new_group_data(browser):
    browser.find_by_id('f-group-create-submit').click()


@when("user submits updated group data")
def ui_schema_submit_updated_group_data(browser):
    browser.find_by_id('f-group-update-submit').click()


@when(parsers.parse("research group {group} is successfully created"))
def ui_group_schema_assert_research_group_created(browser, group):
    assert browser.find_by_css('.alert-success').text == 'Created group research-' + group + '.'


@when(parsers.parse("research group {group} is successfully updated"))
def ui_group_schema_assert_research_group_updated(browser, group):
    # this time the group has to start with the prefix 'research-'!!
    assert browser.find_by_css('.alert-success').text == 'Updated ' + group + ' group properties.'


@when(parsers.parse("datamanager group {group} is successfully created"))
def ui_group_schema_assert_datamanager_group_created(browser, group):
    assert browser.find_by_css('.alert-success').text == 'Created group datamanager-' + group + '.'


@when(parsers.parse("check whether research group properties {group}, {category}, {subcategory}, {schema_id} and {expiration_date} are correct"))
def ui_group_schema_properties_schema_correct(browser, group, category, subcategory, schema_id, expiration_date):
    assert browser.find_by_id('f-group-update-name').value == group
    assert browser.find_by_id('f-group-update-schema-id').value == schema_id
    assert browser.find_by_id('f-group-update-expiration-date').value == expiration_date
    div = browser.find_by_id('f-group-update-category').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == category
    div = browser.find_by_id('f-group-update-subcategory').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == subcategory


@when(parsers.parse("check whether research group properties {group}, {category}, {subcategory} and {expiration_date} for user {user}"), target_fixture="api_response")
def ui_group_schema_properties_default_schema_correct(browser, group, category, subcategory, expiration_date, user):
    # Get the default_schema_id from the yoda configuration
    result = api_request(
        user,
        "schema_get_schemas",
        {}
    )
    default_schema_id = list(result)[1]['data']['schema_default']

    assert browser.find_by_id('f-group-update-name').value == group
    assert browser.find_by_id('f-group-update-schema-id').value == default_schema_id
    assert browser.find_by_id('f-group-update-expiration-date').value == expiration_date
    div = browser.find_by_css('#f-group-update-category').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == category
    div = browser.find_by_css('#f-group-update-subcategory').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == subcategory


@when(parsers.parse("check whether research group properties {category}, {subcategory} and {expiration_date} are correctly updated"))
def ui_group_schema_properties_update_correct(browser, category, subcategory, expiration_date):
    assert browser.find_by_id('f-group-update-expiration-date').value == expiration_date
    div = browser.find_by_css('#f-group-update-category').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == category
    div = browser.find_by_css('#f-group-update-subcategory').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == subcategory


@when(parsers.parse("new group has {category} and {subcategory} set"))
def ui_group_properties_prefilled_categories(browser, category, subcategory):
    div = browser.find_by_css('#f-group-create-category').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == category
    div = browser.find_by_css('#f-group-create-subcategory').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == subcategory


@when(parsers.parse("check whether datamanager group properties {group} and {category} are correct"))
def ui_group_schema_properties_correct(browser, group, category):
    assert browser.find_by_id('f-group-update-name').value == group
    div = browser.find_by_css('#f-group-update-category').find_by_xpath('..').find_by_css('span .select2-selection')
    assert div.find_by_css('.select2-selection__rendered').text == category
