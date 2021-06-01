Feature: Statistics UI

    Scenario: Viewing storage details of research group
        Given user "<user>" is logged in
        And module "stats" is shown
        When user views statistics of group "research-initial"
        Then statistics graph is shown

        Examples:
            | user           |
            | researcher     |
            | datamanager    |

    Scenario: Viewing category storage details as a technicaladmin or datamanager
        Given user "<user>" is logged in
        When module "stats" is shown
        Then storage for "<storage_type>" is shown

        Examples:
            | user           | storage_type          |
            | technicaladmin | Storage (RodsAdmin)   |
            | datamanager    | Storage (Datamanager) |

    Scenario: Export category storage details as a technicaladmin or datamanager
        Given user "<user>" is logged in
        And module "stats" is shown
        When export statistics button is clicked
        Then csv file is downloaded

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |

    Scenario: Viewing resources and managing tiers as a technicaladmin
        Given user "<user>" is logged in
        When module "stats" is shown
        Then resource view is shown
        When user updates "<resource_name>" from "<old_tier>" to "<new_tier>" and "<tier_action>" tier
		
        Examples:
            | user           | resource_name | old_tier | new_tier | tier_action  |
            | technicaladmin | demoResc      | Standard | NEWTIER  | create       |
            | technicaladmin | demoResc      | NEWTIER  | Standard | use_existing |
