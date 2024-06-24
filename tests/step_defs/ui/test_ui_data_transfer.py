# coding=utf-8
"""Settings UI feature tests."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__ = 'GPLv3, see LICENSE'

import os
import time
from pathlib import Path
from urllib.parse import urlparse

import pyperclip
from pytest_bdd import parsers, scenarios, then, when

from conftest import portal_url

scenarios('../../features/ui/ui_data_transfer.feature')


@when("user opens the Data Transfer page")
def ui_data_transfer_page(browser):
    url = "{}/user/data_transfer".format(portal_url)
    browser.visit(url)


@then("user clicks on the iCommands docs page")
def ui_data_transfer_icommands_page(browser):
    url = "https://docs.irods.org/4.2.12/icommands/user/"
    browser.links.find_by_href(url).first.click()
    time.sleep(2)

    # change to the new tab
    browser.windows.current = browser.windows[-1]

    assert browser.url == url
    assert urlparse(browser.url).path == urlparse(url).path


@then(parsers.parse("{title} is shown"))
def ui_data_transfer_page_content(browser, title):
    assert browser.is_text_present(title)


@then('user clicks on iCommands copy button')
def ui_data_transfer_icommands_configuration_copied(browser):
    browser.find_by_id('button1').click()
    clipboard_content = pyperclip.paste()
    assert clipboard_content is not None


@then(parsers.parse("user clicks on iCommands download button and configuration file is downloaded as {format}"))
def ui_data_transfer_icommands_configuration_downloaded(browser, tmpdir, format):
    browser.find_by_id('download-button1').click()
    if os.name == "nt":
        assert True
        return

    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if os.path.basename(str(child)) == "irods_environment.{}".format(format):
            assert True
            return
    raise AssertionError()


@then('user clicks on Gocommands tab')
def ui_data_transfer_gocommands_tab(browser):
    browser.find_by_text('Gocommands').click()


@then("user clicks on the Gocommands docs page")
def ui_data_transfer_gocommands_page(browser):
    url = "https://github.com/cyverse/gocommands/blob/main/README.md"
    browser.links.find_by_href(url).first.click()
    time.sleep(2)

    # change to the new tab
    browser.windows.current = browser.windows[-1]

    assert browser.url == url
    assert urlparse(browser.url).path == urlparse(url).path


@then('user clicks on Gocommands copy button')
def ui_data_transfer_go_commands_configuration_copied(browser):
    browser.find_by_id('button2').click()
    clipboard_content = pyperclip.paste()

    assert clipboard_content is not None


@then(parsers.parse("user clicks on Gocommands download button and configuration file is downloaded as {format}"))
def ui_data_transfer_gocommands_configuration_downloaded(browser, tmpdir, format):
    browser.find_by_id('download-button2').click()

    if os.name == "nt":
        assert True
        return

    root_dir = Path(tmpdir).parent
    if os.name == "nt":
        download_dir = root_dir.joinpath("pytest-splinter0/splinter/download/")
    else:
        download_dir = root_dir.joinpath("pytest-splintercurrent/splinter/download/")

    for child in download_dir.iterdir():
        if os.path.basename(str(child)) == "config.{}".format(format):
            assert True
            return
    raise AssertionError()
