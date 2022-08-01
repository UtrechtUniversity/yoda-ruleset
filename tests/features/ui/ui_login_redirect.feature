Feature: Login Redirects

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
        When user <user> logs in after being redirected
        Then the user is redirected to <page>

        Examples:
        | user          | page       |
        | researcher    | /research/ |
