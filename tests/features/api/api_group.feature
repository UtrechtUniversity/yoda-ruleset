@api
Feature: Group API

    Scenario Outline: Group data
        Given user <user> is authenticated
        And the Yoda group data API is queried
        Then the response status code is "200"
        And group <group> exists

        Examples:
            | user                | group                       |
            | researcher          | research-initial            |
            | groupmanager        | research-initial            |
            | functionaladminpriv | research-initial            |
            | datamanager         | datamanager-test-automation |
            | functionaladminpriv | priv-admin                  |
            | technicaladmin      | priv-category-add           |


    Scenario Outline: Group categories
        Given user <user> is authenticated
        And the Yoda group categories API is queried
        Then the response status code is "200"
        And category <category> exists

        Examples:
            | user        | category        |
            | researcher  | test-automation |
            | datamanager | test-automation |


    Scenario Outline: Group subcategories
        Given user <user> is authenticated
        And the Yoda group subcategories API is queried with <category>
        Then the response status code is "200"
        And subcategory <subcategory> exists

        Examples:
            | user        | category        | subcategory      |
            | researcher  | test-automation | metadata-schemas |
            | datamanager | test-automation | metadata-schemas |
            | researcher  | test-automation | metadata-schemas |
            | datamanager | test-automation | metadata-schemas |


    Scenario Outline: Group search users
        Given user <user> is authenticated
        And the user searches for users matching <pattern>
        Then the response status code is "200"
        And the result is equal to <users>

        Examples:
            | user         | pattern    | users                                                                                         |
            | datamanager  | functional | functionaladmingroup#tempZone, functionaladmincategory#tempZone, functionaladminpriv#tempZone |
            | datamanager  | tech       | technicaladmin#tempZone                                                                       |
            | groupmanager | tech       | technicaladmin#tempZone                                                                       |


    Scenario Outline: Group creation
        Given user <user> is authenticated
        And the group "<group_name>" does not exist
        And the user creates a new group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" is created

        Examples:
            | user                | group_name               |
            | functionaladminpriv | research-api-test-group  |
            | functionaladminpriv | research-api-test1-group |
            | technicaladmin      | not-a-yoda-group         |


    @deposit
    Scenario Outline: Deposit group creation
        Given user <user> is authenticated
        And the group "<group_name>" does not exist
        And the user creates a new deposit group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" is created

        Examples:
            | user                | group_name        |
            | functionaladminpriv | deposit-api-test2 |
            | technicaladmin      | deposit-api-test3 |


    Scenario Outline: Datamanager group creation
        Given user <user> is authenticated
        And the group "<group_name>" does not exist
        And the user creates a new datamanager group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" is created
        # api-test is for creating a datamanager group with functionaladminpriv.
        # api-test1 is for making sure that can still create a datamanager
        # group with technical admin.

        Examples:
            | user                | group_name            |
            | functionaladminpriv | datamanager-api-test  |
            | technicaladmin      | datamanager-api-test1 |


    Scenario Outline: Group update
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user updates group "<group_name>"
        Then the response status code is "200"
        And the update to group "<group_name>" is persisted

        Examples:
            | user                | group_name              |
            | functionaladminpriv | research-api-test-group |
            | functionaladminpriv | datamanager-api-test    |
            | technicaladmin      | datamanager-api-test1   |
            | technicaladmin      | not-a-yoda-group        |


    Scenario Outline: Adding user to group
        Given user <user> is authenticated
        And the user "sterlingarcher" is not a member of group "<group_name>"
        And the user adds user "sterlingarcher" to the group "<group_name>"
        Then the response status code is "200"
        And user "sterlingarcher" is now a member of the group "<group_name>"

        Examples:
            | user                | group_name              |
            | functionaladminpriv | research-api-test-group |
            | functionaladminpriv | datamanager-api-test    |
            | technicaladmin      | datamanager-api-test1   |
            | technicaladmin      | not-a-yoda-group        |


    Scenario Outline: Group user update role
        Given user <user> is authenticated
        And the user "sterlingarcher" is a member of group "<group_name>"
        And the user updates the role of user "sterlingarcher" in group "<group_name>"
        Then the response status code is "200"
        And the role of user "sterlingarcher" in group "<group_name>" is updated

        Examples:
            | user                | group_name              |
            | functionaladminpriv | research-api-test-group |
            | functionaladminpriv | datamanager-api-test    |
            | technicaladmin      | datamanager-api-test1   |
            | technicaladmin      | not-a-yoda-group        |


    Scenario Outline: Remove user from group
        Given user <user> is authenticated
        And the user "sterlingarcher" is a member of group "<group_name>"
        And the user removes user "sterlingarcher" from the group "<group_name>"
        Then the response status code is "200"
        And user "sterlingarcher" is no longer a member of the group "<group_name>"

        Examples:
            | user                | group_name              |
            | functionaladminpriv | research-api-test-group |
            | functionaladminpriv | datamanager-api-test    |
            | technicaladmin      | datamanager-api-test1   |
            | technicaladmin      | not-a-yoda-group        |


    Scenario Outline: Group import CSV
        Given user technicaladmin is authenticated
        And the Yoda API for processing csv group data API is queried for data "csvtestgroup"
        Then the response status code is "200"
        And user "functionaladminpriv@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "datamanager@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "researcher@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "viewer@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "researcher1@example.com" is now a member of the group "research-csvtestgroup"


    Scenario Outline: Group import CSV schema id and expiration date
        Given user technicaladmin is authenticated
        And the Yoda API for processing csv group data API is queried for data "csvtestgroup1"
        Then the response status code is "200"
        And user "datamanager@yoda.test" is now a member of the group "research-csvtestgroup1"


    Scenario Outline: Group import CSV errors
        Given user technicaladmin is authenticated
        And the Yoda API for processing csv group data API is queried for data "<group_name>"
        Then the response status code is "400"

        Examples:
            | group_name         |
            | csv-missing-header |
            | csv-missing-entry  |


    Scenario Outline: Group delete
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user deletes group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" no longer exists

        Examples:
            | user                | group_name               |
            | functionaladminpriv | research-api-test-group  |
            | functionaladminpriv | datamanager-api-test     |
            | functionaladminpriv | research-api-test1-group |
            | technicaladmin      | datamanager-api-test1    |
            | technicaladmin      | research-csvtestgroup    |
            | technicaladmin      | research-csvtestgroup1   |
            | technicaladmin      | not-a-yoda-group         |


    @deposit
    Scenario Outline: Group deposit delete
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user deletes group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" no longer exists

        Examples:
            | user                | group_name        |
            | functionaladminpriv | deposit-api-test2 |
            | technicaladmin      | deposit-api-test3 |
