Feature: Schema API

    Scenario Outline: Schema get schemas
        Given user <user> is authenticated
        And the Yoda schema get schemas API is queried
        Then the response status code is "200"
        And schema <schema> exists

        Examples:
            | user        | schema    |
            | researcher  | core-0    |
            | researcher  | core-1    |
            | researcher  | default-0 |
            | researcher  | default-1 |
            | researcher  | default-2 |
            | datamanager | core-0    |
            | datamanager | core-1    |
            | datamanager | default-0 |
            | datamanager | default-1 |
            | datamanager | default-2 |
