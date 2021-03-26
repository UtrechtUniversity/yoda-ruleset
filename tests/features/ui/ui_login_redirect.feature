Feature: Login Redirects

    Scenario: Redirected to login page
        Given user is not logged in
        When the user navigates to a restricted page
        Then the user is redirected to the login page


    Scenario: After login redirected to homepage
        Given user is not logged in
        When user "researcher" logs in
        Then the user is redirected to "homepage"
 

    Scenario: Logging in redirects to original target
        Given user is not logged in
        And the user navigates to a restricted page
        When user "researcher" logs in after being redirected
        Then the user is redirected to the original restricted page
