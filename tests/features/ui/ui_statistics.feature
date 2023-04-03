Feature: Statistics UI

    Scenario Outline: Viewing storage details of a research group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group <group>
        Then statistics graph is shown

        Examples:
            | user        | group            |
            | researcher  | research-initial |
            | datamanager | research-initial |


    @deposit
    Scenario Outline: Viewing storage details of a deposit group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group <group>
        Then statistics graph is shown

        Examples:
            | user        | group         |
            | researcher  | deposit-pilot |
            | datamanager | deposit-pilot |


    @intake
    Scenario Outline: Viewing storage details of a intake / grp group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group <group>
        Then statistics graph is shown

        Examples:
            | user        | group              |
            | researcher  | grp-intake-initial |
            | researcher  | intake-test2       |
            | datamanager | grp-intake-initial |
            | datamanager | intake-test2       |


    Scenario Outline: Viewing category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        When module "stats" is shown
        Then storage for <categories> is shown

        Examples:
            | user           | categories      |
            | technicaladmin | test-automation |
            | datamanager    | test-automation |


    @intake
    Scenario Outline: Viewing intake category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        When module "stats" is shown
        Then storage for <categories> is shown

        Examples:
            | user           | categories    |
            | technicaladmin | intake-intake |


    Scenario Outline: Export category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        And module "stats" is shown
        When export statistics button is clicked
        Then csv file is downloaded

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |
