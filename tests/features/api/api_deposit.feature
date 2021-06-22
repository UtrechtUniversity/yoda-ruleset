Feature: Deposit API

    Scenario: Deposit API path
        Given user "researcher" is authenticated
        And the Yoda deposit path API is queried
        Then the response status code is "200"

