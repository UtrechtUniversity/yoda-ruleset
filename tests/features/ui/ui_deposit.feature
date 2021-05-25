Feature: Deposit page viewable

    Scenario: Viewing deposit page logged in
        Given user "<user>" is logged in
        And page "deposit" is shown
        Then text "Deposit your data" is shown

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |

    Scenario: Viewing deposit metadata page
        Given user "<user>" is logged in
        And page "deposit/metadata" is shown
        Then text "Add Metadata" is shown

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |

    Scenario: Viewing deposit page logged in
        Given user "<user>" is logged in
        And page "deposit/submit" is shown
        Then text "Submit Deposit" is shown

        Examples:
          | user            |
          | viewer          |
          | researcher      |
          | datamanager     |
          | groupmanager    |
          | technicaladmin  |
