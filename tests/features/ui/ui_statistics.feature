Feature: Statistics UI

    Scenario: Viewing storage details of research group
        Given user "<user>" is logged in
        And module "statistics" is shown
        When user views statistics of group "research-initial"
        Then statistics graph is shown

        Examples:
            | user           |
            | researcher     |
            | datamanager    |

    Scenario: Viewing category storage details as a technicaladmin or datamanager
        Given user "<user>" is logged in
        When module "statistics" is shown
        Then storage for "<storage_type>" is shown

        Examples:
            | user           | storage_type          |
            | technicaladmin | Storage (RodsAdmin)   |
            | datamanager    | Storage (Datamanager) |

    Scenario: Export category storage details as a technicaladmin or datamanager
        Given user "<user>" is logged in
        And module "statistics" is shown
        When export statistics button is clicked
        Then csv file is downloaded

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |
