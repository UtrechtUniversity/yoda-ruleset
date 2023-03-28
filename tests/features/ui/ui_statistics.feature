Feature: Statistics UI

    Scenario Outline: Viewing storage details of a research group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group <group>
        Then statistics graph is shown

        Examples:
            | user        | group                              |
            | researcher  | research-initial                   |
            | datamanager | research-initial                   |
            | researcher  | deposit-pilot                      |
            | datamanager | deposit-pilot                      |
            | researcher  | grp-intake-initial                 |
            | datamanager | grp-intake-initial                 |
            | researcher  | intake-test2                       |
            | datamanager | intake-test2                       |
            | researcher  | datarequests-research-datamanagers |
            | datamanager | datarequests-research-datamanagers |


    Scenario Outline: Viewing category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        When module "stats" is shown
        Then storage for <categories> is shown

        Examples:
            | user           | categories      |
            | technicaladmin | test-automation |
            | datamanager    | test-automation |
            | technicaladmin | intake-intake   |
            | datamanager    | intake-intake   |


    Scenario Outline: Export category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        And module "stats" is shown
        When export statistics button is clicked
        Then csv file is downloaded

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |
