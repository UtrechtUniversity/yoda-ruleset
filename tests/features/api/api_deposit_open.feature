@deposit
Feature: Deposit API (open)

    Scenario: Deposit created
        Given user researcher is authenticated
        And the Yoda deposit create API is queried
        Then the response status code is "200"
        And deposit path is returned


    Scenario Outline: Deposit upload data
        Given user researcher is authenticated
        And deposit exists
        And a file <file> is uploaded in deposit
        Then the response status code is "200"

        Examples:
            | file                        |
            | deposit_open_test_file1.txt |
            | deposit_open_test_file2.txt |
            | deposit_open_test_file3.txt |


    Scenario: Deposit document data
        Given user researcher is authenticated
        And deposit exists
        And metadata JSON is created in deposit
        And data access restriction is open
        Then the response status code is "200"


    Scenario: Deposit status
        Given user researcher is authenticated
        And deposit exists
        And the Yoda deposit status API is queried
        Then the response status code is "200"
        And deposit status is returned


    Scenario: Deposit submit
        Given user researcher is authenticated
        And deposit exists
        And the Yoda deposit submit API is queried
        Then the response status code is "200"


    Scenario Outline: Deposit accessible for viewer
        Given user researcher is authenticated
        And deposit exists
        And deposit is archived
        And user viewer is authenticated
        And the Yoda browse collections API is queried with <collection>
        Then the response status code is "200"
        And the browse result contains deposit

        Examples:
            | collection                 |
            | /tempZone/home/vault-pilot |
