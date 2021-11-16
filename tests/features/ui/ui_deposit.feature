@deposit
Feature: Deposit UI

  Scenario: Deposit start new deposit
    Given user "researcher" is logged in
    And module "deposit" is shown
    When user starts a new deposit
    And module "deposit" is shown
    Then new deposit is created

  Scenario: Deposit steps
    Given user "researcher" is logged in
    And module "deposit" is shown
    When user clicks on active deposit
    Then upload data step is shown
    When user clicks on document data button
    Then document data step is shown

  Scenario: Deposit thankyou page
    Given user "researcher" is logged in
    And page "deposit/thank-you" is shown
    Then text "Thank you!" is shown
