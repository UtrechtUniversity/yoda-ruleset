Feature: Vault API

    Scenario Outline: Vault meta form save in vault
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda meta form save API is queried with metadata on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault submit
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault submit API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "SUBMITTED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault cancel
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "UNPUBLISHED"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault submit after cancel
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault submit API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "SUBMITTED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault approve
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault approve API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "APPROVED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault secured
        Given user datamanager is authenticated
        And data package exists in <vault>
        Then data package in <vault> status is "PUBLISHED"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault preservable formats lists
        Given user researcher is authenticated
        And the Yoda vault preservable formats lists API is queried
        Then the response status code is "200"
        And preservable formats lists are returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault unpreservable files
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault unpreservable files API is queried with <list> on datapackage in <vault>
        Then the response status code is "200"
        And unpreservable files are returned

        Examples:
            | vault                          | list |
            | /tempZone/home/vault-core-0    | 4TU  |
            | /tempZone/home/vault-default-1 | DANS |
            | /tempZone/home/vault-core-1    | 4TU  |
            | /tempZone/home/vault-default-2 | DANS |


    Scenario Outline: Vault system metadata
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault system metadata API is queried on datapackage in <vault>
        Then the response status code is "200"
        And system metadata is returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault collection details
        Given user researcher is authenticated
        And data package exists in <vault>
        And the Yoda vault collection details API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Revoke read access to research group
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault revoke read access research group API is queried on datapackage in <vault>
        Then the response status code is "200"
        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Revoke grant access to research group
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda vault grant read access research group API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |


    Scenario Outline: Vault get publication terms
        Given user researcher is authenticated
        And the Yoda vault get publication terms API is queried
        Then the response status code is "200"
        And publication terms are returned


    Scenario Outline: Vault get published packages
        Given user researcher is authenticated
        And the Yoda vault get published packages API is queried with <vault>
        Then the response status code is "200"
        And published packages are returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |
