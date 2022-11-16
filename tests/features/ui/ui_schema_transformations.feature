Feature: Schema transformations UI

    Scenario Outline: Transformation of metadata by a user
        Given user researcher is logged in
        And module "research" is shown
        When metadata file <schema_from> for <schema_to> is uploaded by user researcher
        And user browses to folder <folder>
        And file yoda-metadata.json exists in folder
        And user opens metadata form
        And user accepts transformation
        Then user downloads file yoda-metadata.json and checks contents after transformation to <schema_to> from <schema_from>

        Examples:
            | folder             | schema_from | schema_to |
            | research-default-1 | default-0   | default-1 |
            | research-default-2 | default-1   | default-2 |
            | research-default-2 | dag-0       | default-2 |
            | research-teclab-1  | teclab-0    | teclab-1  |
            | research-hptlab-1  | hptlab-0    | hptlab-1  |
