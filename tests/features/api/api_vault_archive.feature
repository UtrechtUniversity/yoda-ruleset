@archive
Feature: Vault Archive API

    Scenario Outline: Vault archive status
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault archive status API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |
