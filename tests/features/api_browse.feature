Feature: Browse API

    Scenario: Browse folder
        Given the Yoda browse folder API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"

        Examples:
            | collection                     | result             |
            | /tempZone/home/research-mdtest | copyfromparent     |
            | /tempZone/home/research-mdtest | yoda-metadata.json |

    Scenario: Browse collections
        Given the Yoda browse collections API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"
        And the browse result does not contain "<notresult>"

        Examples:
            | collection                     | result          | notresult          |
            | /tempZone/home/research-mdtest | copyfromparent  | yoda-metadata.json |
