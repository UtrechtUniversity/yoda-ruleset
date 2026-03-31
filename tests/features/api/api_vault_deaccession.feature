@api
Feature: Vault Deaccession API

    Scenario Outline: Vault deaccession request
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault request deaccession API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "DEACCESSION_REQUESTED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault deaccession cancel
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel deaccession API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "ACTIVE"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault deaccession approve
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault approve deaccession API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "DEACCESSION_APPROVED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault deaccession complete
        Given user datamanager is authenticated
        And data package exists in <vault>
        Then data package in <vault> deaccession status is "DEACCESSION_COMPLETE"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |
