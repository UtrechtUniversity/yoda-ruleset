@api
Feature: Vault Deaccession API

    Scenario Outline: Vault deaccession request
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault request deaccession API is queried with <reason> on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "DEACCESSION_REQUESTED"

        Examples:
            | vault                          | reason                 |
            | /tempZone/home/vault-default-1 | Retention time expired |
            | /tempZone/home/vault-default-2 | Retention time expired |
            | /tempZone/home/vault-default-3 | Retention time expired |
            | /tempZone/home/vault-core-2    | Retention time expired |


    Scenario Outline: Vault deaccession cancel by requester
        Given user <user> is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel deaccession API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "ACTIVE"

        Examples:
            | user           | vault                          |
            | datamanager    | /tempZone/home/vault-default-1 |
            | technicaladmin | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault deaccession approve
        Given user <user> is authenticated
        And data package exists in <vault>
        And the Yoda vault approve deaccession API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> deaccession status is "DEACCESSION_COMPLETE"

        Examples:
            | user                | vault                          |
            | functionaladminpriv | /tempZone/home/vault-default-3 |
            | technicaladmin      | /tempZone/home/vault-core-2    |
