@api
Feature: Ping API

    Scenario Outline: Ping portal for irods and flask sessions
        Given user <user> is authenticated
        And the Yoda ping API is queried
        Then the response status code is "200"
        And response has valid sessions

        Examples:
            | user           | 
            | researcher     | 

    Scenario Outline: Ping portal for sessions not logged in
        # Given user <user> is authenticated
        Given the Yoda ping API is queried without user
        Then the response status code is "200"
        And response has no valid sessions

