Feature: Group API

    Scenario Outline: Group data
        Given user <user> is authenticated
        And the Yoda group data API is queried
        Then the response status code is "200"
        And group <group> exists

        Examples:
            | user        | group               |
            | researcher  | research-initial    |
            | researcher  | research-initial1   |
            | datamanager | datamanager-initial |


    Scenario Outline: Group categories
        Given user <user> is authenticated
        And the Yoda group categories API is queried
        Then the response status code is "200"
        And category <category> exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |


    Scenario Outline: Group subcategories
        Given user <user> is authenticated
        And the Yoda group subcategories API is queried with <category>
        Then the response status code is "200"
        And category <category> exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |


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


    Scenario: Group creation
        Given user technicaladmin is authenticated
        And the group "testGroupie" does not exist
        And the user creates a new group "testGroupie"
        Then the response status code is "200"
        And the group "testGroupie" is created


    Scenario: Group update
        Given user technicaladmin is authenticated
        And the group "testGroupie" exists
        And the user updates group "testGroupie"
        Then the response status code is "200"
        And the update to group "testGroupie" is persisted


    Scenario: Adding user to group
        Given user technicaladmin is authenticated
        And the user "sterlingarcher" is not a member of group "testGroupie"
        And the user adds user "sterlingarcher" to the group "testGroupie"
        Then the response status code is "200"
        And user "sterlingarcher" is now a member of the group "testGroupie"


    Scenario: Group user update role
        Given user technicaladmin is authenticated
        And the user "sterlingarcher" is a member of group "testGroupie"
        And the user updates the role of user "sterlingarcher" in group "testGroupie"
        Then the response status code is "200"
        And the role of user "sterlingarcher" in group "testGroupie" is updated


    Scenario: Remove user from group
        Given user technicaladmin is authenticated
        And the user "sterlingarcher" is a member of group "testGroupie"
        And the user removes user "sterlingarcher" from the group "testGroupie"
        Then the response status code is "200"
        And user "sterlingarcher" is no longer a member of the group "testGroupie"


    Scenario: Group delete
        Given user technicaladmin is authenticated
        And the group "testGroupie" exists
        And the user deletes group "testGroupie"
        Then the response status code is "200"
        And the group "testGroupie" no longer exists
