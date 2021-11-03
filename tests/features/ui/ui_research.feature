Feature: Research UI

    Examples:
        | collection                       |
        | /tempZone/home/research-initial  |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is unlocked

    Scenario Outline: Adding a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user adds a new folder "<folder_new>"
        Then folder "<folder_new>" exists in "<folder>"

        Examples:
            | folder           | folder_new      |
            | research-initial | ui_test_folder1 |
            | research-initial | ui_test_folder2 |
            | research-initial | ui_test_copy    |
            | research-initial | ui_test_move    |

    Scenario Outline: Renaming a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user renames folder "<folder_old>" to "<folder_new>"
        Then folder "<folder_new>" exists in "<folder>"

        Examples:
            | folder           | folder_old      | folder_new              |
            | research-initial | ui_test_folder1 | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2 | ui_test_folder2_renamed |

    Scenario Outline: Copying a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user copies folder "<folder_old>" to "<folder_new>"
        Then user browses to subfolder "<folder_new>"
        And folder "<folder_new>" exists in "<folder_old>"

        Examples:
            | folder           | folder_old   | folder_new   |
            | research-initial | ui_test_copy | ui_test_move |

    Scenario Outline: Moving a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user moves folder "<folder_old>" to "<folder_new>"
        Then user browses to subfolder "<folder_new>"
        And folder "<folder_new>" exists in "<folder_old>"

        Examples:
            | folder           | folder_old   | folder_new   |
            | research-initial | ui_test_move | ui_test_copy |

    Scenario Outline: Deleting a folder
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user deletes folder "<folder_delete>"
        Then folder "<folder_delete>" does not exists in "<folder>"

        Examples:
            | folder           | folder_delete           |
            | research-initial | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2_renamed |
            | research-initial | ui_test_copy            |

    Scenario Outline: Renaming a file
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user browses to subfolder "<subfolder>"
        And user clicks rename file for file "<file_name>"
        When user renames file to "<new_file_name>"
        And new file name "<new_file_name>" is present in folder
        Examples:
            | folder           | subfolder | file_name         | new_file_name     |
            | research-initial | testdata  | lorem.txt         | renamed_lorem.txt |
            | research-initial | testdata  | renamed_lorem.txt | lorem.txt         |
