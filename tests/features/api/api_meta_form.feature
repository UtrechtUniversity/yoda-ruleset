Feature: Meta form API

    Examples:
        | collection                       |
        | /tempZone/home/research-initial  |
        | /tempZone/home/research-initial1 |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is unlocked

    Scenario Outline: Meta form save
        Given user "researcher" is authenticated
        And the Yoda meta form save API is queried with metadata and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"

        Examples:
            | file               |
            | yoda-metadata.json |

    Scenario Outline: Meta form save long content
        Given user "researcher" is authenticated
        And the Yoda meta form save API is queried with long metadata and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"

        Examples:
            | file               |
            | yoda-metadata.json |

    Scenario: Meta form load
        Given user "researcher" is authenticated
        And the Yoda meta form load API is queried with "<collection>"
        Then the response status code is "200"
        And metadata is returned for "<collection>"
