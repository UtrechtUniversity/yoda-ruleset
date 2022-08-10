Feature: Folder UI

    Scenario Outline: Folder lock
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user locks the folder
        Then the folder status is "Locked"
        And provenance log includes "Locked"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder unlock
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user unlocks the folder
        Then the folder status is "Unlocked"
        And provenance log includes "Unlocked"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder submit
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user submits the folder
        Then the folder status is "Submitted"
        And provenance log includes "Submitted"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder unsubmit
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user unsubmits the folder
        Then the folder status is "Unsubmitted"
        And provenance log includes "Unsubmitted"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder resubmit after unsubmit
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user submits the folder
        Then the folder status is "Submitted"
        And provenance log includes "Submitted"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder reject
        Given user datamanager is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user rejects the folder
        Then the folder status is "Rejected"
        And provenance log includes "Rejected"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder resubmit after reject
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user submits the folder
        Then the folder status is "Submitted"
        And provenance log includes "Submitted"

        Examples:
            | folder            |
            | research-initial1 |


    Scenario Outline: Folder accept
        Given user datamanager is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user accepts the folder
        Then the folder status is "Accepted"
        And provenance log includes "Accepted"

        Examples:
            | folder            |
            | research-initial1 |
