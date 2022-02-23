@deposit
Feature: Deposit API (restricted)

    Scenario: Deposit created
        Given user "researcher" is authenticated
        And the Yoda deposit create API is queried
        Then the response status code is "200"
        And deposit path is returned

    Scenario: Deposit upload data
        Given user "researcher" is authenticated
        And deposit exists
        And a file "<file>" is uploaded in deposit
        Then the response status code is "200"

        Examples:
            | file                   |
            | deposit_restricted_test_file1.txt |
            | deposit_restricted_test_file2.txt |
            | deposit_restricted_test_file3.txt |

    Scenario: Deposit document data
        Given user "researcher" is authenticated
        And deposit exists
        And metadata JSON is created in deposit
        And data access restriction is restricted
        Then the response status code is "200"

    Scenario: Deposit status
        Given user "researcher" is authenticated
        And deposit exists
        And the Yoda deposit status API is queried
        Then the response status code is "200"
        And deposit status is returned

    Scenario: Deposit submit
        Given user "researcher" is authenticated
        And deposit exists
        And the Yoda deposit submit API is queried
        Then the response status code is "200"

    Scenario: Deposit not accessible for viewer
        Given user "researcher" is authenticated
        And deposit exists
        And deposit is archived
        And user "viewer" is authenticated
        And the Yoda browse collections API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result does not contain deposit

        Examples:
            | collection                 |
            | /tempZone/home/vault-pilot |
