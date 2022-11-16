Feature: Schema transformations UI

    Scenario Outline: Transformation of schemas by a user
        Given user researcher is logged in
        And module "research" is shown
        When metadata file <schema_from> for <schema_to> is uploaded by user researcher
        And user browses to research with active metadata schema <schema_to>
        And file yoda-metadata.json exists in folder
        And user opens metadata form
        And user accepts transformation
        And user closes metadata form
        Then user downloads file yoda-metadata.json and checks contents after transformation to <schema_to>

        Examples:
            | schema_from | schema_to |
            | dag-0       | default-2 |
