@oidc
Feature: Login OIDC UI

    Scenario Outline: Login using OIDC
        Given user is not logged in
        And the user "<user>" can start the OIDC flow
        When user clicks login with OIDC
        And user "<user>" follows OIDC login process
        Then user "<user>" is logged in

        Examples:
            | user                      |
            | yodaresearcher@gmail.com  |
            | yodadatamanager@gmail.com |
