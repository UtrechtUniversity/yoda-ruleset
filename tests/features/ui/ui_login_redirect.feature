Feature: Login Redirects

    Scenario: Redirected to login page
        Given user is not logged in
        When the user navigates to "<page>"
        Then the user is redirected to the login page
        
        Examples:
        | page       |
        | /test      |


    Scenario: After direct login redirected to homepage
        Given user is not logged in
        When user "<user>" logs in
        Then the user is redirected to "<page>"

        Examples:
        | user          | page      |
        | researcher    | /         |


    Scenario: After redirected login redirected to original target
        Given user is not logged in
        And the user navigates to "<page>"
        When user "<user>" logs in after being redirected
        Then the user is redirected to "<page>"

        Examples:
        | user          | page     |
        | researcher    | /test    |
