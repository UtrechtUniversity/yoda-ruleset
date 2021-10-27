@deposit
Feature: Deposit API

    Scenario: Deposit path
        Given user "researcher" is authenticated
        And the Yoda deposit path API is queried
        Then the response status code is "200"
        And deposit path is returned

    Scenario: Deposit status
        Given user "researcher" is authenticated
        And the Yoda deposit status API is queried
        Then the response status code is "200"
        And deposit status is returned

    Scenario: Deposit clear
        Given user "researcher" is authenticated
        And the Yoda deposit clear API is queried
        Then the response status code is "200"
