Feature: Group UI

    Scenario: Group user add
        Given user "groupmanager" is logged in
        And module "group-manager" is shown
        When user has access to group "<group>" in category "<category>"
        And user adds "<user_add>" to group
        Then user "<user_add>" is added to the group

        Examples:
            | category | group            | user_add  |
            | initial  | research-initial | uipromote |
            | initial  | research-initial | uidemote  |

    Scenario: Group user promote
        Given user "groupmanager" is logged in
        And module "group-manager" is shown
        When user has access to group "<group>" in category "<category>"
        And user promotes "<user_promote>" to group manager
        #Then user "<user_add>" is added to the group

        Examples:
            | category | group            | user_promote |
            | initial  | research-initial | uipromote    |

    Scenario: Group user demote
        Given user "groupmanager" is logged in
        And module "group-manager" is shown
        When user has access to group "<group>" in category "<category>"
        And user demotes "<user_demote>" to viewer
        #Then user "<user_add>" is added to the group

        Examples:
            | category | group            | user_demote |
            | initial  | research-initial | uidemote    |

    Scenario: Group user remove
        Given user "groupmanager" is logged in
        And module "group-manager" is shown
        When user has access to group "<group>" in category "<category>"
        And user removes "<user_remove>" from group
        Then user "<user_remove>" is removed from the group

        Examples:
            | category | group            | user_remove |
            | initial  | research-initial | uipromote   |
            | initial  | research-initial | uidemote    |
