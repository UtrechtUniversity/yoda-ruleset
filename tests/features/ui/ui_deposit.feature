@ui @deposit
Feature: Deposit UI

    Scenario Outline: Deposit open and restricted data package
        # User researcher only has access to deposit-pilot
        Given user researcher is logged in
        And module "deposit" is shown

        When user starts a new deposit
        And module "deposit" is shown

        Given user clicks new deposit
        Then upload data step is shown

        Given data file is uploaded to deposit of deposit group deposit-pilot by user researcher
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


    Scenario Outline: Create deposit with choice of two deposit groups
        # User viewer has access to deposit-pilot and deposit-pilot1
        Given user viewer is logged in
        And module "deposit" is shown

        When user starts a new deposit
        # Go with the default group already selected (deposit-pilot)
        And user clicks to create the deposit

        Then upload data step is shown

        Given module "deposit" is shown
        And user clicks new deposit
        Then upload data step is shown

        Given data file is uploaded to deposit of deposit group deposit-pilot by user viewer
        And open metadata is uploaded by user viewer

        When user clicks on add metadata button
        Then add metadata step is shown

        When module "deposit" is shown
        And user clicks on deposit containing open in title
        And user clicks on add metadata button
        Then add metadata step is shown

        When user goes to submission page
        And user submits data
        And submission is confirmed


    Scenario Outline: Attempt to create deposit with access to no deposit groups
        Given user groupmanager is logged in
        And module "deposit" is shown
        Then the start new deposit button is disabled


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
