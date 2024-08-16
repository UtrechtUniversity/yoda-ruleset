@ui
Feature: Admin UI

    Scenario Outline: Admin user views the admin page
        Given user <user> is logged in
        When module "admin" is shown
        Then the text Administration is shown
        And the Administration option is available in the menu dropdown
        And the Maintenance Banner feature is visible
        And the Portal Theme feature is visible
        And the Publication Terms feature is visible
        # Example 1: technicaladmin is an admin user as the role: rodsadmin
        # Example 2: functionaladminpriv is an admin user in the group: priv-admin

        Examples:
            | user                |
            | technicaladmin      |
            | functionaladminpriv |


    Scenario Outline: Non-admin user views the admin page
        Given user <user> is logged in
        When module "admin" is shown
        Then the text Access forbidden is shown
        And the Administration option is not available in the menu dropdown

        Examples:
            | user       |
            | researcher |


    Scenario Outline: Admin user sets up a default banner message
        Given user <user> is logged in
        When module "admin" is shown
        And the user inputs banner message <message>
        And the user <action> the checkbox to mark the banner as important
        And the user clicks the Set Banner button
        And the user navigates to the home page
        Then the banner displays the message <message>
        And the banner background color is <color>
        # Example 1: Set an unimportant banner message
        # Example 2: Set an important banner message

    Examples:
        | user                | message             | action   | color           |
        | functionaladminpriv | Test banner message | unchecks | text-bg-primary |
        | functionaladminpriv | Test banner message | checks   | text-bg-danger  |


    Scenario Outline: Admin user removes an existing banner message
        Given user <user> is logged in
        And the banner displays the message <message>
        When module "admin" is shown
        And the user clicks the Remove Banner button
        And the user navigates to the home page
        Then the banner does not exist

    Examples:
        | user                | message             |
        | functionaladminpriv | Test banner message |


    Scenario Outline: Admin user sets a new portal theme
        Given user <user> is logged in
        When module "admin" is shown
        And the user changes the portal theme to <theme>
        And the user clicks the Set Theme button
        And the user navigates to the home page
        Then the new theme displays <host name>

    Examples:
        | user                | theme  | host name      |
        | functionaladminpriv | uu_fsw | Social Science |
        | functionaladminpriv | uu_geo | Geo            |
        | functionaladminpriv | uu     | Yoda           |


    Scenario Outline: Admin user previews publication terms
        Given user <user> is logged in
        When module "admin" is shown
        And the user adds text <text> to publication terms
        And the user clicks the Preview Terms button
        Then the added text <text> is shown in the preview window

    Examples:
        | user                | text           |
        | functionaladminpriv | TemporaryTerms |


    Scenario Outline: Admin user updates publication terms
        Given user <user> is logged in
        When module "admin" is shown
        And the user adds text <text> to publication terms
        And the user clicks the Set Terms button
        And the user reloads the page
        Then the text <text> is displayed in the publication terms textarea

    Examples:
        | user                | text           |
        | functionaladminpriv | TemporaryTerms |


    Scenario Outline: Admin user removes the text from publication terms
        Given user <user> is logged in
        When module "admin" is shown
        And the text <text> is displayed in the publication terms textarea
        And the user removes the <text> from publication terms
        And the user clicks the Set Terms button
        And the user reloads the page
        Then the text <text> is not displayed in the publication terms textarea

    Examples:
        | user                | text           |
        | functionaladminpriv | TemporaryTerms |
