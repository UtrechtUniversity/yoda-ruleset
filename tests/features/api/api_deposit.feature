@deposit
Feature: Deposit API

    Scenario: Deposit create
        Given user "researcher" is authenticated
        And the Yoda deposit create API is queried
        Then the response status code is "200"
        And deposit path is returned

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
        Then the response status code is "400"
