@api
Feature: Group API

    Scenario Outline: Group data
        Given user <user> is authenticated
        And the Yoda group data API is queried
        Then the response status code is "200"
        And group <group> exists

        Examples:
            | user        | group                       |
            | researcher  | research-initial            |
            | researcher  | research-initial1           |
            | datamanager | datamanager-test-automation |


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
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |


    Scenario Outline: Group update
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user updates group "<group_name>"
        Then the response status code is "200"
        And the update to group "<group_name>" is persisted

        Examples:
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |


    Scenario Outline: Adding user to group
        Given user <user> is authenticated
        And the user "sterlingarcher" is not a member of group "<group_name>"
        And the user adds user "sterlingarcher" to the group "<group_name>"
        Then the response status code is "200"
        And user "sterlingarcher" is now a member of the group "<group_name>"

        Examples:
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |


    Scenario Outline: Group user update role
        Given user <user> is authenticated
        And the user "sterlingarcher" is a member of group "<group_name>"
        And the user updates the role of user "sterlingarcher" in group "<group_name>"
        Then the response status code is "200"
        And the role of user "sterlingarcher" in group "<group_name>" is updated

        Examples:
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |


    Scenario Outline: Remove user from group
        Given user <user> is authenticated
        And the user "sterlingarcher" is a member of group "<group_name>"
        And the user removes user "sterlingarcher" from the group "<group_name>"
        Then the response status code is "200"
        And user "sterlingarcher" is no longer a member of the group "<group_name>"

        Examples:
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |


    Scenario Outline: Group import CSV
        Given user technicaladmin is authenticated
        And the Yoda API for processing csv group data API is queried
        Then the response status code is "200"
        And user "functionaladminpriv@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "datamanager@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "researcher@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "viewer@yoda.test" is now a member of the group "research-csvtestgroup"
        And user "researcher1@example.com" is now a member of the group "research-csvtestgroup"


    Scenario Outline: Group delete
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user deletes group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" no longer exists

        Examples:
            | user                  | group_name                 |
            | functionaladminpriv   | research-api-test-group    |
            | technicaladmin        | datamanager-api-test-group |
            | technicaladmin        | testGroupie                |
            | technicaladmin        | research-csvtestgroup      |
