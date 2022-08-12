@deposit
Feature: Deposit UI

    Scenario Outline: Deposit open and restricted data package
        Given user researcher is logged in
        And module "deposit" is shown

        When user starts a new deposit
        And module "deposit" is shown

        Given user clicks new deposit
        Then upload data step is shown

        Given data file is uploaded to deposit by user researcher
        And <data_access_restriction> metadata is uploaded by user researcher

        When user clicks on add metadata button
        Then add metadata step is shown

        When module "deposit" is shown
        And user clicks on deposit containing <data_access_restriction> in title
        And user clicks on add metadata button
        Then add metadata step is shown

        When user goes to submission page
        And user submits data
        And submission is confirmed

        Examples:
            | data_access_restriction |
            | open                    |
            | restricted              |


    Scenario: Search for open data package
        Given user viewer is logged in
        And module "deposit" is shown
        When user searches for "UI test Open"
        And clicks on "UI test Open" data package
        And landingpage shows "Open" access
        And all fields contain correct data
        And user copies identifier to clipboard
        And user clicks for map details
        And user clicks for data access with "UI test Open" in title


    Scenario: Search for restricted data package
        Given user viewer is logged in
        And module "deposit" is shown
        When user searches for "UI test Restricted"
        And clicks on "UI test Restricted" data package
        And landingpage shows "Restricted" access
        And all fields contain correct data
        And user copies identifier to clipboard
        And user clicks for map details
