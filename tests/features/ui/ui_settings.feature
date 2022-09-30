Feature: Settings UI

    Scenario Outline: Save user settings
        Given user researcher is logged in
        And module "user/settings" is shown
        When user sets mail notifications to <type>
        And clicks the save button
        Then mail notifications is set to <type>

        Examples:
            | type      |
            | WEEKLY    |
            | DAILY     |
            | IMMEDIATE |
            | OFF       |
