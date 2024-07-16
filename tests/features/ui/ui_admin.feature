@ui
Feature: Admin UI

    Scenario Outline: Admin page view by admin users
        Given user <user> is logged in
        When the user navigates to the admin page
        Then the text Administration is shown
        And Administration option is available in the menu dropdown
        And the banner setup option should be visible

        Examples:
            | user                |
            | technicaladmin      | # Role: irodsadmin
            | functionaladminpriv | # Group: priv-admin


    Scenario Outline: Admin page view by non-admin user
        Given user <user> is logged in
        When the user navigates to the admin page
        Then the text Access forbidden is shown
        And Administration option is not available in the menu dropdown

        Examples:
            | user                |
            | researcher          | # Role: non-admin and Group: non-priv-group


    Scenario Outline: Admin user sets up a default banner message
        Given user <user> is logged in
        When the user navigates to the admin page
        And the user input banner text with message <message>
        And the user <action> the checkbox to mark the banner as important
        And the user click button <button>
        And the user navigates to the home page
        Then the banner display the message <message>
        And the banner background color should be <color>
    # Example 1 :Set an unimportant banner message
    # Exampel 2 :Set an important banner message
    Examples:
        | user                | message             | action     | button     |color           |
        | functionaladminpriv | Test banner message | unchecks   | Set Banner |text-bg-primary |
        | functionaladminpriv | Test banner message | checks     | Set Banner |text-bg-danger  |


    Scenario Outline: Admin user removes an exsting banner message
        Given user <user> is logged in
        And the banner display the message <message>
        When the user navigates to the admin page
        And the user click button <Remove Banner>
        And the user navigates to the home page
        Then the banner does not exist
    Examples:
        | user                | message             | Remove Banner |
        | functionaladminpriv | Test banner message | Remove Banner |
