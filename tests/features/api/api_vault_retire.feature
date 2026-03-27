@api
Feature: Vault Retire API

    Scenario Outline: Vault retirement request
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault request retirement API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> retirement status is "RETIREMENT_REQUESTED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault retirement cancel
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel retirement API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> retirement status is "ACTIVE"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |


    Scenario Outline: Vault retirement approve
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
        Then data package in <vault> retirement status is "RETIRED"

        Examples:
            | vault                           |
            | /tempZone/home/vault-default-3  |
