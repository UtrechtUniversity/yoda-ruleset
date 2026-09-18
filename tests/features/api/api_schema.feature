@api
Feature: Schema API

    Scenario Outline: Schema get schemas
        Given user <user> is authenticated
        And the Yoda schema get schemas API is queried
        Then the response status code is "200"
        And schema <schema> exists

        Examples:
            | user        | schema     |
            | researcher  | core-0     |
            | researcher  | core-1     |
            | researcher  | default-0  |
            | researcher  | default-1  |
            | researcher  | default-2  |
            | researcher  | default-3  |
            | researcher  | epos-msl-0 |
            | researcher  | epos-msl-1 |
            | datamanager | core-0     |
            | datamanager | core-1     |
            | datamanager | default-0  |
            | datamanager | default-1  |
            | datamanager | default-2  |
            | datamanager | default-3  |
            | datamanager | epos-msl-0 |
            | datamanager | epos-msl-1 |


    Scenario Outline: Schema get schemas and default schema
        Given user researcher is authenticated
        And the Yoda schema get schemas API is queried
        Then the response status code is "200"
        And default schema is present


    Scenario Outline: Schema list schemas
        Given user <user> is authenticated
        And the Yoda schema list schemas API is queried
        Then the response status code is "200"
        And list contains schema <schema>

            Examples:
                | user        | schema                  |
                | researcher  | access-rights_1-0-0     |
                | researcher  | citation_1-0-0          |
                | researcher  | descriptive_1-0-0       |
                | researcher  | funding_1-0-0           |
                | researcher  | preservation_1-0-0      |
                | researcher  | related-resources_1-0-0 |
                | researcher  | spatial-coverage_1-0-0  |
                | researcher  | temporal-coverage_1-0-0 |
                | datamanager | access-rights_1-0-0     |
                | datamanager | citation_1-0-0          |
                | datamanager | descriptive_1-0-0       |
                | datamanager | funding_1-0-0           |
                | datamanager | preservation_1-0-0      |
                | datamanager | related-resources_1-0-0 |
                | datamanager | spatial-coverage_1-0-0  |
                | datamanager | temporal-coverage_1-0-0 |
