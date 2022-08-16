@oidc
Feature: Login UI

    Scenario Outline: Internal user login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> logs in
        Then user <user> is logged in

        Examples:
            | user           |
            | researcher     |
            | datamanager    |
            | technicaladmin |


    Scenario Outline: External user login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> logs in
        Then user <user> is logged in

        Examples:
            | user                  |
            | alice@otherdomain.com |


    Scenario Outline: OIDC user login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> follows OIDC login process
        Then user <user> is logged in

        Examples:
            | user                  |
            | researcher@yoda.test  |
            | datamanager@yoda.test |


    Scenario Outline: Invalid OIDC login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> follows OIDC login process
        Then incorrect username / password message is shown

        Examples:
            | user                |
            | chewbacca@yoda.test |


    Scenario Outline: After redirected OIDC login redirected to original target
        Given user is not logged in
        And the user navigates to <page>
        And the user is redirected to the login page
        When user <user> enters email address
        And user <user> follows OIDC login process
        Then the user is redirected to <page>

        Examples:
        | user                  | page       |
        | researcher@yoda.test  | /research/ |
        | datamanager@yoda.test | /research/ |
