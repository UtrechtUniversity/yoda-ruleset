@api @retire
Feature: Vault Retire API

    Scenario Outline: Vault request retirement
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault request retirement API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> retirement status is "RETIREMENT_REQUESTED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault cancel retirement
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel retirement API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> retirement status is ""

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault approve retirement
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault approve retirement API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> retirement status is "RETIREMENT_APPROVED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault retired
        Given user datamanager is authenticated
        And data package exists in <vault>
        And data package in <vault> retirement status is "RETIRED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |