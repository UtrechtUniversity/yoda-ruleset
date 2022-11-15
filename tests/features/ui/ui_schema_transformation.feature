Feature: Schema transformation UI

    Scenario Outline: Transformation of schemas by a user
        Given user researcher is logged in
        And module "research" is shown
        Given metadata file <schema_from> for <schema_to> is uploaded by user researcher
        When user browses to research with active metadata schema <schema_to>
        Then file yoda-metadata.json exists in folder
        When user opens metadata form
        When user accepts transformation
        When user closes metadata form
        When user downloads file yoda-metadata.json and checks contents after transformation to <schema_to>

        Examples:
            | schema_from | schema_to |
            | dag-0       | default-2 |
