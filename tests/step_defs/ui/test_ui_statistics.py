# coding=utf-8
"""Statistics UI feature tests."""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
from pathlib import Path

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_statistics.feature')


@when(parsers.parse('user views statistics of group "{group}"'))
def ui_statistics_group_view(browser, group):
    browser.find_by_css('a.list-group-item[data-name={}]'.format(group)).click()


@when('export statistics button is clicked')
def ui_statistics_export(browser):
    # For now prevent downloading on windows platforn
    if os.name == "nt":
        return
    # Only click when not in Windows
    browser.find_by_css('a.btn.btn-primary.btn-sm').click()


@then('statistics graph is shown')
def ui_statistics_graph_shown(browser):
    browser.is_text_not_present("No storage information found.", wait_time=1)


@then('storage for "<storage_type>" is shown')
def ui_statistics_category_storage(browser, storage_type):
    browser.is_text_present(storage_type, wait_time=1)


@then('csv file is downloaded')
def ui_statistics_csv_downloaded(browser, tmpdir):
    # Short cut for windows environment to prevent testing for actual downloaded files.
    # This as a dialog prevents forced downloading but a choice is requested.
    # Either choose top open with Excel or download.
    # This choice cannot be automated
    # Therefore, skip this test
    if os.name == "nt":
        assert True
        return

    # Below code is correct in itself and therefore left here in full
    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if str(child)[-4:] == ".csv":
            os.remove(child)
            assert True
        else:
            raise AssertionError()


# Resource tier management tests
@then('resource view is shown')
def ui_resource_view_is_shown(browser):
    assert browser.find_by_css('.resources')


@when('user updates "<resource_name>" from "<old_tier>" to "<new_tier>" and "<tier_action>" tier')
def ui_resource_tier_is_updated_for_resource(browser, resource_name, old_tier, new_tier, tier_action):
    # Find index of resource_name in resource table
    index = 0
    for resource in browser.find_by_css('.resource'):
        if resource.value.find(resource_name) >= 0:
            break
        index = index + 1

    # Check if tier is set correctly
    assert(browser.find_by_css('.resource-tier')[index].value.find(old_tier) >= 0)

    # Click in resource table on row resource_name
    browser.find_by_css('.resource')[index].click()

    # Activate tier select
    browser.find_by_css('.select2-selection').click()

    browser.find_by_css('.select2-search__field').fill(new_tier)
    create_new_tier = ''
    if tier_action == 'create':
        create_new_tier = ' (create)'
    browser.find_by_text(new_tier + create_new_tier).click()

    # Click update tier button
    browser.find_by_css('.update-resource-properties-btn').click()


@then('"<resource_name>" has tier "<new_tier>"')
def ui_resource_has_tier(browser, resource_name, new_tier):
    # Find index of resource_name in resource table
    index = 0
    for resource in browser.find_by_css('.resource'):
        if resource.value.find(resource_name) >= 0:
            break
        index = index + 1

    # Check if tier is set correctly
    assert (browser.find_by_css('.resource', wait_time=30)[index].value.find(new_tier) >= 0)
