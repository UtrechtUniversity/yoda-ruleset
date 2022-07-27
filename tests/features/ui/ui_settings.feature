Feature: Settings UI

    Scenario: Save user settings
        Given user researcher is logged in
        And module "user/settings" is shown
        When user checks mail notifications checkbox
        And clicks the save button
        Then mail notifications checkbox is checked
