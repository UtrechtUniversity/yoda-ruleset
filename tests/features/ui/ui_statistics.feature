Feature: Statistics UI

    Scenario: Viewing storage consumption of research group
        Given user "<user>" is logged in
        And module "statistics" is shown
        When user views statistics of group "research-initial"
        Then statistics graph is shown

        Examples:
            | user           |
            | researcher     |
            | datamanager    |

    Scenario: Viewing category storage consumption as a technicaladmin or datamanager
        Given user "<user>" is logged in
        When module "statistics" is shown
        Then storage for "<storage_type>" is shown

              Examples:
                | user           | storage_type          |
                | technicaladmin | Storage (RodsAdmin)   |
                | datamanager    | Storage (Datamanager) |
