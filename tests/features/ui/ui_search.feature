Feature: Search UI

    Scenario: Search file
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches by filename with "<file>"
        Then result "<result>" is found

        Examples:
            | file               | result                                |
            | yoda-metadata.json | /research-initial1/yoda-metadata.json |

    Scenario: Search folder
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches by folder with "<folder>"
        Then result "<result>" is found

        Examples:
            | folder            | result             |
            | research-initial1 | /research-initial1 |

    Scenario: Search metadata
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches by metadata with "<metadata>"
        Then result "<result>" is found

        Examples:
            | metadata | result             |
            | yoda     | /research-initial1 |

    Scenario: Search folder status
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches by folder status with "<status>"
        Then result "<result>" is found

        Examples:
            | status           | result             |
            | research:SECURED | /research-initial1 |
