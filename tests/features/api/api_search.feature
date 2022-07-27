Feature: Search API

    Scenario Outline: Search file
        Given user researcher is authenticated
        And the Yoda search file API is queried with <file>
        Then the response status code is "200"
        And result <result> is found

        Examples:
            | file               | result                                 |
            | yoda-metadata.json | /research-core-0/yoda-metadata.json    |
            | yoda-metadata.json | /research-default-1/yoda-metadata.json |
            | yoda-metadata.json | /research-core-1/yoda-metadata.json    |
            | yoda-metadata.json | /research-default-2/yoda-metadata.json |


    Scenario Outline: Search folder
        Given user researcher is authenticated
        And the Yoda search folder API is queried with <folder>
        Then the response status code is "200"
        And result <result> is found

        Examples:
            | folder            | result             |
            | research-initial  | /research-initial  |
            | research-initial1 | /research-initial1 |


    Scenario Outline: Search metadata
        Given user researcher is authenticated
        And the Yoda search metadata API is queried with <metadata>
        Then the response status code is "200"
        And result <result> is found

        Examples:
            | metadata | result             |
            | yoda     | /research-initial  |
            | yoda     | /research-initial1 |


    Scenario Outline: Search folder status
        Given user researcher is authenticated
        And the Yoda search folder status API is queried with <status>
        Then the response status code is "200"
        And result <result> is found

        Examples:
            | status           | result              |
            | research:SECURED | /research-core-0    |
            | research:SECURED | /research-default-1 |
            | research:SECURED | /research-core-1    |
            | research:SECURED | /research-default-2 |
