@archive
Feature: Vault Archive API

    Scenario Outline: Vault archival status
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault archival status API is queried on datapackage in <vault>
        Then the response status code is "200"
        And the data package in <vault> is archivable

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault archive
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault archive API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> archival status is "archive"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault archived
        Given user datamanager is authenticated
        And data package exists in <vault>
        Then data package in <vault> archival status is "archived"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |
