@sram
Feature: Group API

    Scenario Outline: Group creation
        Given user <user> is authenticated
        And the group "<group_name>" does not exist
        And the user creates a new SRAM group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" is created

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |


    Scenario Outline: Group update
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user updates group "<group_name>"
        Then the response status code is "200"
        And the update to group "<group_name>" is persisted

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |


    Scenario Outline: Adding user to group
        Given user <user> is authenticated
        And the user "researcher@yoda.test" is not a member of group "<group_name>"
        And the user adds user "researcher@yoda.test" to the group "<group_name>"
        Then the response status code is "200"
        And user "researcher@yoda.test" is now a member of the group "<group_name>"

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |


    Scenario Outline: Group user update role
        Given user <user> is authenticated
        And the user "researcher@yoda.test" is a member of group "<group_name>"
        And the user updates the role of user "researcher@yoda.test" in group "<group_name>"
        Then the response status code is "200"
        And the role of user "researcher@yoda.test" in group "<group_name>" is updated

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |


    Scenario Outline: Remove user from group
        Given user <user> is authenticated
        And the user "researcher@yoda.test" is a member of group "<group_name>"
        And the user removes user "researcher@yoda.test" from the group "<group_name>"
        Then the response status code is "200"
        And user "researcher@yoda.test" is no longer a member of the group "<group_name>"

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |


    Scenario Outline: Group delete
        Given user <user> is authenticated
        And the group "<group_name>" exists
        And the user deletes group "<group_name>"
        Then the response status code is "200"
        And the group "<group_name>" no longer exists

        Examples:
            | user                  | group_name                   |
            | functionaladminpriv   | research-api-test-group-sram |
