Feature: Research UI

    Examples:
        | collection                       |
        | /tempZone/home/research-initial  |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is unlocked

    Scenario Outline: Multi-select moving files / folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user multi-select moves files / folders to "<folder_new>"
        Then user browses to subfolder "<folder_new>"
        And files / folders exist in "<folder_new>"
        And files / folders do not exist in "<folder_new>"

        Examples:
            | folder           | folder_new   |
            | research-initial | clone        |


    Scenario Outline: Multi-select copying files / folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user browses to subfolder "<folder_new>"
        And user multi-select copies files / folders to "<folder>"
        Then files / folders exist in "<folder_new>"
        And module "research" is shown
        And user browses to folder "<folder>"
        And files / folders exist in "<folder>"

        Examples:
            | folder           | folder_new   |
            | research-initial | clone        |


    Scenario Outline: Multi-select deleting files / folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user browses to subfolder "<subfolder>"
        And user multi-select deletes files / folders
        Then files / folders do not exist in "<subfolder>"

        Examples:
            | folder           | subfolder |
            | research-initial | clone     |
