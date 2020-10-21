Feature: Group API

    Scenario: Group data
        Given user "<user>" is authenticated
        And the Yoda group data API is queried
        Then the response status code is "200"
        And group "<group>" exists

        Examples:
            | user        | group               |
            | researcher  | research-initial    |
            | researcher  | research-initial1   |
            | datamanager | datamanager-initial |

    Scenario: Group data filtered
        Given user "<user>" is authenticated
        And the Yoda group data filtered API is queried with "<user>" and "<zone>"
        Then the response status code is "200"
        And group "<group>" exists

        Examples:
            | user        | zone     | group               |
            | researcher  | tempZone | research-initial    |
            | researcher  | tempZone | research-initial1   |
            | datamanager | tempZone | datamanager-initial |

    Scenario: Group categories
        Given user "<user>" is authenticated
        And the Yoda group categories API is queried
        Then the response status code is "200"
        And category "<category>" exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |

    Scenario: Group subcategories
        Given user "<user>" is authenticated
        And the Yoda group subcategories API is queried with "<category>"
        Then the response status code is "200"
        And category "<category>" exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |

    Scenario: Group user exists
        Given user "<user>" is authenticated
        And the Yoda group user exists API is queried with "<group>" and "<user>"
        Then the response status code is "200"
        And response is "<exists>"

        Examples:
            | user        | group                           | exists |
            | researcher  | research-initial                | True   |
            | researcher  | research-initial1               | True   |
            | datamanager | datamanager-initial             | True   |
            | researcher  | datamanager-initial             | False  |
            | datamanager | research-initial1               | False  |
