@ui
Feature: Data Transfer UI

    Scenario Outline: Save user settings for mail notifications
        Given user <user> is logged in
        And module "user/data_transfer" is shown

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |
