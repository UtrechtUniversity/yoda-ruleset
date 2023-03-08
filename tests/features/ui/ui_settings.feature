Feature: Settings UI

    Scenario Outline: Save user settings for mail notification
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

    Scenario Outline: Save user settings for group manager
        Given user <user> is logged in
        And module "user/settings" is shown
        When uuser sets group manager view to {type}
        And clicks the save button
        Then group manager view is set to <type>

        Examples:
            | user           | type    |
            | researcher     | LIST    |
            | researcher     | TREE    |
            | technicaladmin | LIST    |
            | technicaladmin | TREE    |