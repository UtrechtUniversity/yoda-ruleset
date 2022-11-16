Feature: Schema transformations API

    Scenario Outline: Transformation of metadata
        Given user researcher is authenticated
        And a metadata file with schema <schema_from> is uploaded to folder with schema <schema_to>
        Then transformation of metadata is successful for collection <schema_to>
        And the response status code is "200"

        Examples:
            | schema_from | schema_to |
            | dag-0       | default-2 |
            | default-0   | default-1 |
            | default-1   | default-2 |
            | teclab-0    | teclab-1  |
            | hptlab-0    | hptlab-1  |
