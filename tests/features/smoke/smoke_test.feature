@smoke
Feature: Smoke tests

    Scenario Outline: Meta form save and load
        Given user smoke_account is authenticated
        And metadata JSON exists in <collection>
        And the Yoda meta form load API is queried with <collection>
        Then the response status code is "200"
        And metadata is returned for <collection>

        Examples:
            | collection                       |
            | /tempZone/home/research-smoke-test  |


    Scenario Outline: Browse research folder
        Given user smoke_account is authenticated
        And the Yoda browse folder API is queried with <collection>
        Then the response status code is "200"
        And the browse result contains <result>

        Examples:
            | collection                      | result             |
            | /tempZone/home/research-smoke-test | yoda-metadata.json |


    Scenario Outline: Research folder lock
        Given user smoke_account is authenticated
        And the Yoda folder lock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                          | status |
            | /tempZone/home/research-smoke-test | LOCKED |


    Scenario Outline: Research folder get locks
        Given user smoke_account is authenticated
        And the Yoda folder get locks API is queried with <folder>
        Then the response status code is "200"
        And folder locks contains <folder>

        Examples:
          | folder                          |
          | /tempZone/home/research-smoke-test |


    Scenario Outline: Research folder unlock
        Given user smoke_account is authenticated
        And the Yoda folder unlock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status |
            | /tempZone/home/research-smoke-test   | FOLDER |


    Scenario Outline: Research folder submit
        Given user smoke_account is authenticated
        And metadata JSON exists in <folder>
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status    |
            | /tempZone/home/research-smoke-test   | SUBMITTED |


    Scenario Outline: Research folder unsubmit
        Given user smoke_account is authenticated
        And the Yoda folder unsubmit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status |
            | /tempZone/home/research-smoke-test   | FOLDER |

    Scenario Outline: Research folder resubmit after unsubmit
        Given user smoke_account is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status    |
            | /tempZone/home/research-smoke-test   | SUBMITTED |


    Scenario Outline: Research folder reject
        Given user smoke_account is authenticated
        And the Yoda folder reject API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status   |
            | /tempZone/home/research-smoke-test   | REJECTED |


    Scenario Outline: Research folder resubmit after reject
        Given user smoke_account is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status    |
            | /tempZone/home/research-smoke-test   | SUBMITTED |


    Scenario Outline: Research folder accept
        Given user smoke_account is authenticated
        And the Yoda folder accept API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                            | status   |
            | /tempZone/home/research-smoke-test   | ACCEPTED |


    Scenario Outline: Research folder secured
        Given user smoke_account is authenticated
        Then folder <folder> status is <status>

        Examples:
            | folder                            | status   |
            | /tempZone/home/research-smoke-test   | SECURED  |


    Scenario Outline: Vault meta form save in vault
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda meta form save API is queried with metadata on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault submit
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault submit API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "SUBMITTED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault cancel
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault cancel API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "UNPUBLISHED"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault submit after cancel
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault submit API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "SUBMITTED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault approve
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault approve API is queried on datapackage in <vault>
        Then the response status code is "200"
        And data package in <vault> status is "APPROVED_FOR_PUBLICATION"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault secured
        Given user smoke_account is authenticated
        And data package exists in <vault>
        Then data package in <vault> status is "PUBLISHED"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault preservable formats lists
        Given user smoke_account is authenticated
        And the Yoda vault preservable formats lists API is queried
        Then the response status code is "200"
        And preservable formats lists are returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault unpreservable files
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault unpreservable files API is queried with <list> on datapackage in <vault>
        Then the response status code is "200"
        And unpreservable files are returned

        Examples:
            | vault                          | list |
            | /tempZone/home/vault-smoke-test   | 4TU  |
            | /tempZone/home/vault-smoke-test   | DANS |


    Scenario Outline: Vault system metadata
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault system metadata API is queried on datapackage in <vault>
        Then the response status code is "200"
        And system metadata is returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault collection details
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault collection details API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |


    Scenario Outline: Vault revoke read access to research group
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault revoke read access research group API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                           |
            | /tempZone/home/vault-smoke-test |


    Scenario Outline: Vault grant read access to research group
        Given user smoke_account is authenticated
        And data package exists in <vault>
        And the Yoda vault grant read access research group API is queried on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                           |
            | /tempZone/home/vault-smoke-test |


    Scenario Outline: Vault get publication terms
        Given user smoke_account is authenticated
        And the Yoda vault get publication terms API is queried
        Then the response status code is "200"
        And publication terms are returned


    Scenario Outline: Vault get published packages
        Given user smoke_account is authenticated
        And the Yoda vault get published packages API is queried with <vault>
        Then the response status code is "200"
        And published packages are returned

        Examples:
            | vault                          |
            | /tempZone/home/vault-smoke-test   |
