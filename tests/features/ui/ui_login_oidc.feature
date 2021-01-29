@oidc
Feature: Login OIDC UI

    Scenario: Login using OIDC
        Given user is not logged in
        And login page is shown
        When user clicks login with OIDC
        And user "<user>" follows OIDC login process
        Then user "<user>" is logged in

        Examples:
            | user                      |
            | yodaresearcher@gmail.com  |
            | yodadatamanager@gmail.com |
