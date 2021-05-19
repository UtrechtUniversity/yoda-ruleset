Feature: Homepage Loggedin

    Scenario: Viewing homepage logged in
        Given user "<user>" is logged in
        And homepage is shown
        # When the user navigates to homepage
        Then username <user> is shown
        ## inside .header-logo-text-content p

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |
