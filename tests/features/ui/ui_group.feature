@ui
Feature: Group UI

    Scenario Outline: Group member add
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user selects tree view
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
        When user selects tree view
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
        When user selects tree view
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
        When user selects tree view
        When user selects group <group> in subcategory <subcategory> and category <category>
        And searches for member <member>
        Then only member <member> is shown

        Examples:
            | category        | subcategory | group            | member     |
            | test-automation | initial     | research-initial | researcher |


    Scenario Outline: Group search
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects tree view
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
        And user clicks upload button and uploads csv "csv-import-test.csv"
        Then there are 4 groups presented
        When user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv
        And check number of rows is 4
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


    Scenario: Imports group CSV schema id and expiration date
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user opens group import dialog
        And user clicks upload button and uploads csv "csv-import-test-exp-schema.csv"
        Then there are 2 groups presented
        When user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv
        And check number of rows is 2
        And click on imported row 0 and check group properties
        And find group member "groupmanager@yoda.test"
        And find group member "researcher@yoda.test"
        And user opens group import dialog
        And click on imported row 1 and check group properties
        And schema id is "default-3"
        And expiration date is "2027-01-01"
        And find group member "groupmanager@yoda.test"


    Scenario Outline: Group research create with default schema id
        Given user <user> is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And groupname is set to <group>
        And category is set to <category>
        And subcategory is set to <subcategory>
        And expiration date is set to <expiration_date>
        When user submits new group data
        And research group <group> is successfully created
        And check whether research group properties <group>, <category>, <subcategory> and <expiration_date> for user functionaladminpriv

        Examples:
            | user                | category          | subcategory       | group             | expiration_date |
            | functionaladminpriv | test-automation   | test-automation   | ui-test-group     | 2030-12-25      |
            | functionaladminpriv | test-datamanager  | test-datamanager  | test-datamanager  | 2030-12-25      |
            | technicaladmin      | test-datamanager1 | test-datamanager1 | test-datamanager1 | 2030-12-25      |


    Scenario Outline: Create new research group starting from same (sub)category of active group at that moment
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user selects tree view
        When user selects group <group> in subcategory <subcategory> and category <category>
        When user opens add group dialog
        And new group has <category> and <subcategory> set

        Examples:
            | category        | subcategory | group            |
            | test-automation | initial     | research-initial |


    Scenario Outline: Group research update
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user selects tree view
        When user selects group <group> in subcategory <subcategory> and category <category>
        When category is updated to <category>
        And subcategory is updated to <subcategory>
        And expiration date is updated to <expiration_date>
        When user submits updated group data
        And research group <group> is successfully updated
        And check whether research group properties <category>, <subcategory> and <expiration_date> are correctly updated

        Examples:
            | category        | subcategory      | group                  | expiration_date |
            | test-automation | test-automation | research-ui-test-group  | 2035-12-31      |


    Scenario Outline: Group datamanager create
        Given user <user> is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And category is set to <category>
        And group type is set to datamanager
        And subcategory is set to <subcategory>
        When user submits new group data
        And datamanager group <group> is successfully created
        And check whether datamanager group properties <group> and <category> are correct

        Examples:
            | user                | category          | subcategory       | group              |
            | functionaladminpriv | test-datamanager  | test-datamanager  | test-datamanager   |
            | technicaladmin      | test-datamanager1 | test-datamanager1 | test-datamanager1  |


    @deposit
    Scenario Outline: Group deposit create
        Given user <user> is logged in
        And module "group_manager" is shown
        When user opens add group dialog
        And group type is set to deposit
        And category is set to <category>
        And groupname is set to <group>
        And subcategory is set to <subcategory>
        When user submits new group data
        And deposit group <group> is successfully created
        And check whether deposit group properties <group>, <category> and <subcategory> for user <user>

        Examples:
            | user                | category        | subcategory     | group    |
            | functionaladminpriv | test-automation | test-automation | ui-test2 |
            | technicaladmin      | test-automation | test-automation | ui-test3 |


    Scenario Outline: Group remove
        Given user <user> is logged in
        And module "group_manager" is shown
        When user selects group <group> in subcategory <subcategory> and category <category>
        And user clicks remove group
        And user confirms group removal

        Examples:
            | user                | category          | subcategory       | group                         |
            | functionaladminpriv | test-automation   | test-automation   | research-ui-test-group        |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group1      |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group2      |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group3      |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group4      |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group5      |
            | functionaladminpriv | test-automation   | csv-test          | research-csv-test-group6      |
            | functionaladminpriv | test-datamanager  | test-datamanager  | datamanager-test-datamanager  |
            | functionaladminpriv | test-datamanager  | test-datamanager  | research-test-datamanager     |
            | technicaladmin      | test-datamanager1 | test-datamanager1 | datamanager-test-datamanager1 |
            | technicaladmin      | test-datamanager1 | test-datamanager1 | research-test-datamanager1    |


    @deposit
    Scenario Outline: Group deposit remove
        Given user <user> is logged in
        And module "group_manager" is shown
        When user selects group <group> in subcategory <subcategory> and category <category>
        And user clicks remove group
        And user confirms group removal

        Examples:
            | user                | category        | subcategory     | group            |
            | functionaladminpriv | test-automation | test-automation | deposit-ui-test2 |
            | technicaladmin      | test-automation | test-automation | deposit-ui-test3 |


    Scenario Outline: Select group in tree view and check group properties are set and active in tree view
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects tree view
        And user selects group <group> in subcategory <subcategory> and category <category>
        And checks group properties for <group>
        And correct row in tree is active for <group>
        When user selects list view
        And correct row in list view is active for <group>

        Examples:
            | category        | subcategory | group            |
            | test-automation | initial     | research-initial |


    Scenario Outline: Select group in list view and check group properties are set and active in tree view
        Given user researcher is logged in
        And module "group_manager" is shown
        When user selects list view
        And user selects group <group> in list view
        And checks group properties for <group>
        And correct row in list view is active for <group>
        When user selects tree view
        And correct row in tree is active for <group>

        Examples:
            | group            |
            | research-initial |


    Scenario Outline: Searching results in different lists depending on user (role)
        Given user <user> is logged in
        And module "group_manager" is shown
        When user enters search argument <search>
        And autocomplete returns <suggestions> suggestions

        Examples:
            | user        | search | suggestions |
            | researcher  | yoda   | 5           |
            | datamanager | yoda   | 5           |
            | researcher  | core   | 3           |
            | datamanager | core   | 3           |


    Scenario: Collapsing group properties persists between logins
        Given user functionaladminpriv is logged in
        And module "group_manager" is shown
        When user clicks group properties header
        And user logs out
        And user functionaladminpriv logs in
        And module "group_manager" is shown
        Then group properties is collapsed


    Scenario: Collapsing group properties persists between groups
        Given user groupmanager is logged in
        And module "group_manager" is shown
        When user selects tree view
        When user selects group research-initial in subcategory initial and category test-automation
        And user clicks group properties header
        When user selects group research-revisions in subcategory initial and category test-automation
        Then group properties is collapsed
