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


    Scenario Outline: Schema get building blocks
        Given user <user> is authenticated
        And the Yoda schema get building blocks schemas API is queried
        Then the response status code is "200"
        And building block <block> is present

        Examples:
            | user        | block                   |
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


    Scenario Outline: Schema post composed schemas
        Given user <user> is authenticated
        And the Yoda schema post composed schemas API is queried with <identifier>
        Then the response status code is "200"

        Examples:
            | user                | identifier |
            | functionaladminpriv | api1       |
            | functionaladminpriv | api2       |


    Scenario Outline: Schema put composed schemas
        Given user <user> is authenticated
        And the Yoda schema put composed schemas API is queried with <identifier>
        Then the response status code is "200"

        Examples:
            | user                | identifier |
            | functionaladminpriv | api1       |
            | functionaladminpriv | api2       |


    Scenario Outline: Schema get composed schemas
        Given user <user> is authenticated
        And the Yoda schema get composed schemas API is queried
        Then the response status code is "200"
        And list contains schema <schema>

        Examples:
            | user                | schema |
            | researcher          | api1   |
            | datamanager         | api2   |
            | functionaladminpriv | api1   |
            | functionaladminpriv | api2   |


    Scenario Outline: Schema get composed schema
        Given user <user> is authenticated
        And the Yoda schema get composed schema API is queried with <identifier>
        Then the response status code is "200"
        And schema contains building block <block>

        Examples:
            | user                | identifier | block               |
            | researcher          | api1       | citation_1-0-0      |
            | datamanager         | api2       | descriptive_1-0-0   |
            | functionaladminpriv | api1       | preservation_1-0-0  |
            | functionaladminpriv | api2       | access-rights_1-0-0 |


    Scenario Outline: Schema delete composed schemas
        Given user <user> is authenticated
        And the Yoda schema delete composed schemas API is queried with <identifier>
        Then the response status code is "200"

        Examples:
            | user                | identifier |
            | functionaladminpriv | api1       |
            | functionaladminpriv | api2       |


    Scenario Outline: Schema get composed schema after deletion
        Given user <user> is authenticated
        And the Yoda schema get composed schema API is queried with <identifier>
        Then the response status code is "400"

        Examples:
            | user                | identifier |
            | researcher          | api1       |
            | datamanager         | api2       |
            | functionaladminpriv | api1       |
            | functionaladminpriv | api2       |
