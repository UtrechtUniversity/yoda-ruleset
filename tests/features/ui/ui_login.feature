@oidc
Feature: Login UI

    Scenario Outline: External user login
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> logs in
        Then user <user> is logged in

        Examples:
            | user                  |
            | alice@otherdomain.com |

    Scenario Outline: Forced OIDC login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> follows OIDC login process
        Then user <user> is logged in

        Examples:
            | user                      |
            | yodaresearcher@gmail.com  |
            | yodadatamanager@gmail.com |
            | researcher@yoda.test      |
            | datamanager@yoda.test     |

    Scenario Outline: After redirected OIDC login redirected to original target
        Given user is not logged in
        And the user navigates to <page>
        And the user is redirected to the login page
        When user <user> enters email address
        And user <user> follows OIDC login process
        Then the user is redirected to <page>

        Examples:
        | user                     | page       |
        | yodaresearcher@gmail.com | /research/ |
