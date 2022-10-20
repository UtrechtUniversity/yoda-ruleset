Feature: Group UI

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


    Scenario Outline: For one specific user retrieve a list of its groups. Click one group
        Given user datamanager is logged in
        And module "group_manager" is shown
        When user opens group search dialog
        And searches for groups of user <user_search>
        Then a list of groups is shown in the dialog
        When user clicks first found group

        Examples:
            | user_search |
            | researcher  |


    Scenario Outline: A datamanager imports group definitions through uploading a CSV file
        Given user datamanager is logged in
        And module "group_manager" is shown
        When user opens group import dialog
        And user clicks upload button
        And user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv and check number of rows
        And click on imported row 0 and check group properties
        And find groupmember "manager@uu.nl"
        And user opens group import dialog
        And click on imported row 1 and check group properties
        And find groupmember "member1@uu.nl"