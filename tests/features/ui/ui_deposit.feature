@deposit
Feature: Deposit UI

  Scenario: Deposit page home
    Given user "researcher" is logged in
    And page "deposit" is shown
    Then text "Deposit upload" is shown

  Scenario: Deposit meta page
    Given user "researcher" is logged in
    And page "deposit/metadata/" is shown
    Then text "Metadata for your deposit" is shown

  Scenario: Deposit submit page
    Given user "researcher" is logged in
    And page "deposit/submit/" is shown
    Then text "Submit your data package" is shown

  Scenario: Deposit thankyou page
    Given user "researcher" is logged in
    And page "deposit/thankyou/" is shown
    Then text "Thank you" is shown
