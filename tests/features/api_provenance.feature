Feature: Provenance API

    Scenario: Provenance log
        Given the Yoda provenance log API is queried with "<collection>"
        Then the response status code is "200"
        And provenance log is returned

        Examples:
            | collection                      |
            | /tempZone/home/research-initial |
