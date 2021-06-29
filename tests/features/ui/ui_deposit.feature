Feature: Deposit UI

  Scenario: Deposit page home
    Given user "researcher" is logged in
    And page "deposit" is shown
    Then text "Deposit your data" is shown

  Scenario: Deposit meta page
    Given user "researcher" is logged in
    And page "deposit/metadata/" is shown
    Then text "Deposit Metadata for" is shown

  Scenario: Deposit submit page
    Given user "researcher" is logged in
    And page "deposit/submit/" is shown
    Then text "Submit Deposit" is shown
