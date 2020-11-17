Feature: Vault API

    Examples:
        | vault                         |
        | /tempZone/home/vault-initial1 |

    Scenario: Vault submit
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault submit API is queried on datapackage in "<vault>"
        Then the response status code is "200"
        And data package status is "SUBMITTED_FOR_PUBLICATION"

    Scenario: Vault cancel
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault cancel API is queried on datapackage in "<vault>"
        Then the response status code is "200"
        And data package status is "UNPUBLISHED"

    Scenario: Vault submit after cancel
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault submit API is queried on datapackage in "<vault>"
        Then the response status code is "200"
        And data package status is "SUBMITTED_FOR_PUBLICATION"

    Scenario: Vault approve
        Given user "datamanager" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault approve API is queried on datapackage in "<vault>"
        Then the response status code is "200"
        And data package status is "APPROVED_FOR_PUBLICATION"

    Scenario: Vault preservable formats lists
        Given user "researcher" is authenticated
        And the Yoda vault preservable formats lists API is queried
        Then the response status code is "200"
        And preservable formats lists are returned

    Scenario: Vault unpreservable files
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault unpreservable files API is queried with "<list>" on datapackage in "<vault>"
        Then the response status code is "200"
        And unpreservable files are returned

        Examples:
            | list |
            | 4TU  |
            | DANS |

    Scenario: Vault system metadata
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault system metadata API is queried on datapackage in "<vault>"
        Then the response status code is "200"

    Scenario: Vault collection details
        Given user "researcher" is authenticated
        And data package exists in "<vault>"
        And the Yoda vault collection details API is queried on datapackage in "<vault>"
        Then the response status code is "200"

    Scenario: Vault get publication terms
        Given user "researcher" is authenticated
        And the Yoda vault get publication terms API is queried
        Then the response status code is "200"
        And publication terms are returned
