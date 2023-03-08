Feature: Group UI

    Scenario Outline: Group member add
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And user adds <member_add> to group
        Then test if member <member_add> is added to the group

        Examples:
            | category        | subcategory | group            | member_add      |
            | test-automation | initial     | research-initial | user1@yoda.test |
            | test-automation | initial     | research-initial | user2@yoda.test |


    Scenario Outline: Group member change role
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And user selects two members <member1> and <member2>
        And user changes roles to <new_role>
        Then role change is successful

        Examples:
            | category        | subcategory | group            | member1         | member2         | new_role |
            | test-automation | initial     | research-initial | user1@yoda.test | user2@yoda.test | manager  |
            | test-automation | initial     | research-initial | user1@yoda.test | user2@yoda.test | normal   |
            | test-automation | initial     | research-initial | user1@yoda.test | user2@yoda.test | reader   |


    Scenario Outline: Group member remove
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And user selects two members <member1> and <member2>
        And user removes selected members
        And remove members from group is confirmed
        Then members successfully removed

        Examples:
            | category        | subcategory | group            | member1         | member2         |
            | test-automation | initial     | research-initial | user1@yoda.test | user2@yoda.test |


    Scenario Outline: Group member search
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And searches for member <member>
        Then only member <member> is shown

        Examples:
            | category        | subcategory | group            | member     |
            | test-automation | initial     | research-initial | researcher |


    Scenario Outline: Group search
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And searches for group <group>
        Then only group <group> is shown

        Examples:
            | category        | subcategory | group            |
            | test-automation | initial     | research-initial |


    Scenario: Imports group from CSV
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user opens group import dialog
        And user clicks upload button
        And user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv and check number of rows
        And click on imported row 0 and check group properties
        And find group member "groupmanager@yoda.test"
        And user opens group import dialog
        And click on imported row 1 and check group properties
        And find group member "researcher@yoda.test"
        And user opens group import dialog
        And click on imported row 2 and check group properties
        And find group member "datamanager@yoda.test"
        And user opens group import dialog
        And click on imported row 3 and check group properties
        And find group member "viewer@yoda.test"


    Scenario Outline: Group research create
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And groupname is set to <group>
        And category is set to <category>
        And subcategory is set to <subcategory>
        And schema id is set to <schema_id>
        And expiration date is set to <expiration_date>
        When user submits new group data
        And research group <group> is successfully created
        And check whether research group properties <group>, <category>, <subcategory>, <schema_id> and <expiration_date> are correct

        Examples:
            | category        | subcategory     | group         | schema_id | expiration_date  |
            | test-automation | test-automation | ui-test-group | teclab-1  | 2030-12-25       |


    Scenario Outline: Group research update
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        When category is updated to <category>
        And subcategory is updated to <subcategory>
        And expiration date is updated to <expiration_date>
        When user submits updated group data
        And research group <group> is successfully updated
        And check whether research group properties <category>, <subcategory> and <expiration_date> are correctly updated

        Examples:
            | category              | subcategory        | group                                | expiration_date |
            | test-automation | test-automation | research-ui-test-group  | 2035-12-31         |


    Scenario Outline: Group datamanager create
        Given user technicaladmin is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And category is set to <category>
        And subcategory is set to <subcategory>
        And group type is set to datamanager
        When user submits new group data
        And datamanager group <group> is successfully created
        And check whether datamanager group properties <group> and <category> are correct

        Examples:
            | category         | subcategory      | group            |
            | test-datamanager | test-datamanager | test-datamanager |


    Scenario Outline: Within TREE list select a group and check whether flatlist and group properties are set correctly
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        When user selects group <group> in subcategory <subcategory> and category <category>
        And checks group properties for <group>
        And correct row in tree is active for <group>
        When user selects FLAT group list
        And correct row in flatlist is active for <group>
 
        Examples:
            | category        | subcategory | group            |
            | test-automation | initial     | research-initial |


    Scenario Outline: Within FLAT list select group and check whether tree and group properties are set correctly
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects FLAT group list
        When user selects group <group> in flatlist
        When checks group properties for <group>
        And correct row in flatlist is active for <group>
        When user selects TREE group list
        And correct row in tree is active for <group>

        Examples:
            | group            |
            | research-initial |


    Scenario Outline: Search in flatlist on group and user and check shortening of result list
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects FLAT group list
        And user searches for groups <group> in flatlist
        And user searches for users <user> in flatlist

        Examples:
            | group  | user  |
            | res    | data  |


    Scenario Outline: Search in treelist on group and user and check shortening of result list
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        And user searches for groups <group> in tree
        And user searches for users <user> in tree

        Examples:
            | group  | user |
            | res    | data |


    Scenario Outline: Searching for users results in different lists depending on user (role)
        Given user <user> is logged in
        And module "group_manager" is shown
        When user selects TREE group list
        And user enters search argument <search_user>
        And finds <result_count> users

        Examples:
            | user        | search_user | result_count |
            | researcher  | yoda        | 5            |
            | datamanager | yoda        | 13           |
