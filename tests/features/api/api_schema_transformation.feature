Feature: Schema transformation API


    Scenario Outline: Transformation of metadata
        Given user researcher is authenticated
        And a metadata file with schema <schema_from> is uploaded to folder with schema <schema_to>
        # Then the response status code is "200"
        And transformation of metadata is successful for collection <schema_to>
        # Then the response status code is "200"

        Examples:
            | schema_from | schema_to |
            | dag-0       | default-2 |

