@ui
Feature: Admin UI

    Scenario Outline: Admin page view
        Given user <user> is logged in 
        When user opens link to admin page
        Then the text Administration is shown
        And Administration option is available in the menu dropdown

        Examples:
            | user                |  
            | technicaladmin      | # Role: irodsadmin
            | functionaladminpriv | # Group: priv-admin-group
            | technicaladmin      | # Role: irodsadmin and Group: priv-group-add #TODO: FUnctionaladmivpriv, add user to needed group


    Scenario Outline: Admin page view by non-admin user
        Given user <user> is logged in 
        When user opens link to admin page
        Then the text Access forbidden is shown
        And Administration option is not available in the menu dropdown

        Examples:
            | user                | 
            | researcher          | # Role: non-admin and Group: non-priv-group
