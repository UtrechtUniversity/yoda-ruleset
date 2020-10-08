Feature: Search API

    Scenario: Search file
        Given the Yoda search file API is queried with "<file>"
        Then the response status code is "200"
        And result "<result>" is found

        Examples:
            | file               | result                                |
            | yoda-metadata.json | /research-initial1/yoda-metadata.json |

    Scenario: Search folder
        Given the Yoda search folder API is queried with "<folder>"
        Then the response status code is "200"
        And result "<result>" is found

        Examples:
            | folder            | result             |
            | research-initial1 | /research-initial1 |

    Scenario: Search metadata
        Given the Yoda search metadata API is queried with "<metadata>"
        Then the response status code is "200"
        And result "<result>" is found

        Examples:
            | metadata | result             |
            | yoda     | /research-initial1 |

    Scenario: Search folder status
        Given the Yoda search folder status API is queried with "<status>"
        Then the response status code is "200"
        And result "<result>" is found

        Examples:
            | status           | result             |
            | research:SECURED | /research-initial1 |
