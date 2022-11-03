Feature: Group UI

    Scenario Outline: Group create
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And groupname is set to <group>
        And category is set to <category>
        And schemaid is set to <schema_id>
        When user submits new group data
        And group <group> is successfully created
        And check whether group properties <group>, <category> and <schema_id> are correct
        # alle testgroepen onderbrengen in ui category / groepen
        # alle groepen gemaakt door ui tests ook weer verwijderd
        Examples:
            | group         | category | schema_id |
            | ui-test-group | core-0   | teclab-1  |


    Scenario Outline: Group user add
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And user adds <user_add> to group
        Then user <user_add> is added to the group

        Examples:
            | category | group            | user_add  |
            | initial  | research-initial | uipromote |
            | initial  | research-initial | uidemote  |


    Scenario Outline: Group user promote
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And user promotes <user_promote> to group manager

        Examples:
            | category | group            | user_promote |
            | initial  | research-initial | uipromote    |


    Scenario Outline: Group user demote
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And user demotes <user_demote> to viewer

        Examples:
            | category | group            | user_demote |
            | initial  | research-initial | uidemote    |


    Scenario Outline: Group user remove
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And user removes <user_remove> from group
        Then user <user_remove> is removed from the group

        Examples:
            | category | group            | user_remove |
            | initial  | research-initial | uipromote   |
            | initial  | research-initial | uidemote    |

    Scenario Outline: Group member search
        Given user researcher is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And searches for member <member>
        Then only member <member> is shown

        Examples:
            | category | group            | member     |
            | initial  | research-initial | researcher |


    Scenario Outline: Group search
        Given user researcher is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And searches for group <group>
        Then only group <group> is shown

        Examples:
            | category | group            |
            | initial  | research-initial |


    Scenario Outline: List groups of users
        Given user datamanager is logged in
        And module "group_manager" is shown
        When user opens group search dialog
        And searches for groups of user <user_search>
        Then a list of groups is shown in the dialog
        When user clicks first found group

        Examples:
            | user_search |
            | researcher  |


    Scenario: Imports group from CSV
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user opens group import dialog
        And user clicks upload button
        And user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv and check number of rows
        And click on imported row 0 and check group properties
        And find groupmember "groupmanager@yoda.test"
        And user opens group import dialog
        And click on imported row 1 and check group properties
        And find groupmember "researcher@yoda.test"
        And user opens group import dialog
        And click on imported row 2 and check group properties
        And find groupmember "datamanager@yoda.test"
        And user opens group import dialog
        And click on imported row 3 and check group properties
        And find groupmember "viewer@yoda.test"


    Scenario Outline: Group remove
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user has access to group <group> in category <category>
        And user clicks remove group
        And user confirms group removal

        Examples:
            | category  | group                    |
            | csv-test  | research-csv-test-group1 |
            | csv-test  | research-csv-test-group2 |
            | csv-test  | research-csv-test-group3 |
            | csv-test  | research-csv-test-group4 |
            | core-0    | research-ui-test-group   |
