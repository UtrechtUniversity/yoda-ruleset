Feature: Meta form API

    Scenario: Meta form save
        Given user "researcher" is authenticated
        And the Yoda meta form save API is queried with metadata and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"

        Examples:
            | collection                       | file               |
            | /tempZone/home/research-initial1 | yoda-metadata.json |


    Scenario: Meta form load
        Given user "researcher" is authenticated
        And the Yoda meta form load API is queried with "<collection>"
        Then the response status code is "200"
        And metadata is returned for "<collection>"

        Examples:
            | collection                       |
            | /tempZone/home/research-initial1 |
