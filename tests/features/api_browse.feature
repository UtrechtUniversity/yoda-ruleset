Feature: Browse API

    Scenario: Browse folder
        Given the Yoda browse folder API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"

        Examples:
            | collection                     | result         |
            | /tempZone/home/research-mdtest | copyfromparent |

    Scenario: Browse collections
        Given the Yoda browse collections API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"

        Examples:
            | collection                     | result         |
            | /tempZone/home/research-mdtest | copyfromparent |
