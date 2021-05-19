Feature: Homepage Loggedin

    Scenario: Viewing homepage logged in
        Given user "<user>" is logged in
        And page "/" is shown
        Then username "<user>" is shown
        ## inside .header-logo-text-content p

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |
