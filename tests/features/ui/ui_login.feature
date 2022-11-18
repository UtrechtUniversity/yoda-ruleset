Feature: Login UI

    Scenario Outline: User login flow
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


    Scenario Outline: Invalid user login flow
        Given user is not logged in
        And the user is at the login gate
        When user <user> enters email address
        And user <user> logs in
        Then incorrect username / password message is shown

        Examples:
            | user                |
            | chewbacca@yoda.test |


    Scenario Outline: Redirected to login page
        Given user is not logged in
        When the user navigates to <page>
        Then the user is redirected to the login page

        Examples:
        | page       |
        | /research/ |


    Scenario Outline: After direct login redirected to homepage
        Given user is not logged in
        When user <user> logs in
        Then the user is redirected to <page>

        Examples:
            | user          | page      |
            | researcher    | /         |


    Scenario Outline: After redirected login redirected to original target
        Given user is not logged in
        And the user navigates to <page>
        And the user is redirected to the login page
        When user <user> enters email address
        And user <user> logs in
        Then the user is redirected to <page>

        Examples:
            | user          | page       |
            | researcher    | /research/ |
            | datamanager   | /research/ |
