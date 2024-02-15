@ui @archive
Feature: Vault Archive UI

    Scenario Outline: Vault archive
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for archival
        And user confirms archival of data package
        Then the data package archive status is "Scheduled for archive"
        And provenance log includes "Scheduled for archive"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault archived
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package archive status is "Archived"
        And provenance log includes "Archived"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault unarchive
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for unarchival
        And user confirms unarchival of data package
        Then the data package archive status is "Scheduled for unarchive"
        And provenance log includes "Scheduled for unarchive"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault unarchived
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then provenance log includes "Unarchived"

        Examples:
            | vault          |
            | vault-initial1 |
