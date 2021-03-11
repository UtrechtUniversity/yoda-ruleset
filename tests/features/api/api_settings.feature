Feature: Settings API

    Scenario: Settings Save
        Given user "researcher" is authenticated
        And the Yoda settings save API is queried with "<file>"
        Then the response status code is "200"

    Scenario: Settings Load
        Given user "researcher" is authenticated
        And the Yoda settings load API is queried with "<folder>"
        Then the response status code is "200"
