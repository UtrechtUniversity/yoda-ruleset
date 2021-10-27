Feature: Homepage logged in

    Scenario Outline: Viewing homepage logged in
        Given user "<user>" is logged in
        And page "/" is shown
        Then username "<user>" is shown

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |
