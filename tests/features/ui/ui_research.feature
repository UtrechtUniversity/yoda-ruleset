Feature: Research UI

    Scenario: Adding a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user adds a new folder "<folder_new>"
        Then folder "<folder_new>" exists in "<folder>"

        Examples:
            | folder           | folder_new      |
            | research-initial | ui_test_folder1 |
            | research-initial | ui_test_folder2 |

    Scenario: Renaming a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user renames folder "<folder_old>" to "<folder_new>"
        Then folder "<folder_new>" exists in "<folder>"

        Examples:
            | folder           | folder_old      | folder_new              |
            | research-initial | ui_test_folder1 | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2 | ui_test_folder2_renamed |

    Scenario: Deleting a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user deletes folder "<folder_delete>"
        Then folder "<folder_delete>" does not exists in "<folder>"

        Examples:
            | folder           | folder_delete           |
            | research-initial | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2_renamed |
