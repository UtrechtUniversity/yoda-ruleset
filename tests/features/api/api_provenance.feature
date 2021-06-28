Feature: Provenance API

    Scenario Outline: Provenance log
        Given user "<user>" is authenticated
        And the Yoda provenance log API is queried with "<collection>"
        Then the response status code is "200"
        And provenance log is returned

        Examples:
            | user        |  collection                     |
            | researcher  | /tempZone/home/research-initial |
            | datamanager | /tempZone/home/research-initial |
