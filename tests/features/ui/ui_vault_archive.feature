Feature: Vault Archive UI

    Scenario Outline: Vault archive
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for archival
        And user confirms archival of data package
        Then the data package archive status is "Submitted for archive"
        And provenance log includes "Submitted for archive"

        Examples:
            | vault          |
            | vault-initial1 |
