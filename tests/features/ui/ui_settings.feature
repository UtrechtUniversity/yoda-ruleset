Feature: Settings UI

    Scenario Outline: Save user settings
        Given user <user> is logged in
        And module "user/settings" is shown
        When user sets mail notifications to <type>
        And clicks the save button
        Then mail notifications is set to <type>

        Examples:
            | user           | type      |
            | researcher     | WEEKLY    |
            | researcher     | DAILY     |
            | researcher     | IMMEDIATE |
            | researcher     | OFF       |
            | technicaladmin | WEEKLY    |
            | technicaladmin | DAILY     |
            | technicaladmin | IMMEDIATE |
            | technicaladmin | OFF       |
    
    Scenario Outline: Save user settings
        Given user <user> is logged in
        And module "user/settings" is shown
        When user sets number of items to <type>
        And clicks the save button
        Then number of items is set to <type>

        Examples:
            | user           | type      |
            | researcher     | 10        |
            | researcher     | 25        |
            | researcher     | 50        |
            | researcher     | 100       |
            | technicaladmin | 10        |
            | technicaladmin | 25        |
            | technicaladmin | 50        |
            | technicaladmin | 100       |
