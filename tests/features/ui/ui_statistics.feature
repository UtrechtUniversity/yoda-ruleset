Feature: Statistics UI

    Scenario Outline: Viewing storage details of a group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group <group>
        Then statistics graph is shown

        Examples:
            | user        | group            |
            | researcher  | research-initial |
            | researcher  | deposit-pilot    |
            | datamanager | research-initial |
            | datamanager | deposit-pilot    |

    
    Scenario Outline: Viewing category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        When module "stats" is shown
        Then storage for <categories> is shown

        Examples:
            | user           | categories      |
            | technicaladmin | test-automation |
            | technicaladmin | intake-intake2  |
            | datamanager    | test-automation |


    Scenario Outline: Export category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        And module "stats" is shown
        When export statistics button is clicked
        Then csv file is downloaded

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |
