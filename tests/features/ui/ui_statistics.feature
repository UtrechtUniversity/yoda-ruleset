Feature: Statistics UI

    Scenario Outline: Viewing storage details of a research group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group research-initial
        Then statistics graph is shown

        Examples:
            | user        |
            | researcher  |
            | datamanager |


    Scenario Outline: Viewing storage details of a deposit group
        Given user <user> is logged in
        And module "stats" is shown
        When groupdetails contains initial text
        When user views statistics of group deposit-pilot
        Then statistics graph is shown

        Examples:
            | user        |
            | researcher  |
            | datamanager |


    Scenario Outline: Viewing category storage details as a technicaladmin or datamanager
        Given user <user> is logged in
        When module "stats" is shown
        Then storage for <categories> is shown

        Examples:
            | user           | categories      |
            | technicaladmin | test-automation |
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
