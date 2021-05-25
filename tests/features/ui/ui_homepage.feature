Feature: Homepage Loggedin

    Scenario: Viewing homepage logged in
        Given user "<user>" is logged in
        And page "" is shown
        Then username "<user>" is shown

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |
