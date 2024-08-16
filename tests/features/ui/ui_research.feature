@ui
Feature: Research UI

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Copying a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <subfolder>
        And user copies file <file> to <folder>
        And user browses to folder <folder>
        Then file <file> exists in folder

        Examples:
            | folder           | subfolder | file                         |
            | research-initial | testdata  | lorem.txt                    |
            | research-initial | testdata  | SIPI_Jelly_Beans_4.1.07.tiff |


    Scenario Outline: Copy and overwrite a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <subfolder>
        And user copies file <file> to <folder>
        And user accepts overwriting file
        And user browses to folder <folder>
        Then file <file> exists in folder

        Examples:
            | folder           | subfolder | file      |
            | research-initial | testdata  | lorem.txt |


    Scenario Outline: Renaming a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user renames file <file> to <file_renamed>
        Then file <file> exists in folder

        Examples:
            | folder           | file      | file_renamed      |
            | research-initial | lorem.txt | lorem_renamed.txt |


    Scenario Outline: Moving a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user moves file <file> to <subfolder>
        Then file <file> does not exist in folder
        And user browses to subfolder <subfolder>
        And file <file> exists in folder

        Examples:
            | folder           | subfolder | file              |
            | research-initial | testdata  | lorem_renamed.txt |


    Scenario Outline: Move and overwrite a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user moves file <file> to <subfolder>
        And user accepts overwriting file
        Then file <file> does not exist in folder
        And user browses to subfolder <subfolder>
        And file <file> exists in folder

        Examples:
            | folder           | subfolder | file                         |
            | research-initial | testdata  | SIPI_Jelly_Beans_4.1.07.tiff |


    Scenario Outline: Deleting a file
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <subfolder>
        And user deletes file <file>
        Then file <file> does not exist in folder


        Examples:
            | folder           | subfolder | file              |
            | research-initial | testdata  | lorem_renamed.txt |


    Scenario Outline: Adding a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user adds a new folder <folder_new>
        Then folder <folder_new> exists in <folder>

        Examples:
            | folder           | folder_new        |
            | research-initial | ui_test_folder1   |
            | research-initial | ui_test_folder2   |
            | research-initial | ui_test_copy      |
            | research-initial | ui_test_move      |
            | research-initial | ui_test_overwrite |


    Scenario Outline: Renaming a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user renames folder <folder_old> to <folder_new>
        Then folder <folder_new> exists in <folder>

        Examples:
            | folder           | folder_old      | folder_new              |
            | research-initial | ui_test_folder1 | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2 | ui_test_folder2_renamed |


    Scenario Outline: Copying a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user copies folder <folder_old> to <folder_new>
        Then user browses to subfolder <folder_new>
        And folder <folder_new> exists in <folder_old>

        Examples:
            | folder           | folder_old        | folder_new   |
            | research-initial | ui_test_copy      | ui_test_move |
            | research-initial | ui_test_overwrite | ui_test_copy |


    Scenario Outline: Copying and overwriting a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user copies folder <folder_old> to <folder_new>
        And user accepts overwriting folder
        Then user browses to subfolder <folder_new>
        And folder <folder_new> exists in <folder_old>

        Examples:
            | folder           | folder_old   | folder_new   |
            | research-initial | ui_test_copy | ui_test_move |


    Scenario Outline: Moving a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user moves folder <folder_old> to <folder_new>
        Then user browses to subfolder <folder_new>
        And folder <folder_new> exists in <folder_old>

        Examples:
            | folder           | folder_old   | folder_new   |
            | research-initial | ui_test_move | ui_test_copy |


    Scenario Outline: Moving and overwriting a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user moves folder <folder_old> to <folder_new>
        And user accepts overwriting folder
        Then user browses to subfolder <folder_new>
        And folder <folder_new> exists in <folder_old>

        Examples:
            | folder           | folder_old        | folder_new   |
            | research-initial | ui_test_overwrite | ui_test_copy |

    Scenario Outline: Checksum report of added empty folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user adds a new folder <folder_new>
        And user browses to subfolder <folder_new>
        And user open checksum report
        Then user cannot download <format> checksum report

        Examples:
            | folder           | folder_new                | format |
            | research-initial | ui_test_empty_checksum1   | csv    |
            | research-initial | ui_test_empty_checksum2   | txt    |


    Scenario Outline: Deleting a folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user deletes folder <folder_delete>
        Then folder <folder_delete> does not exists in <folder>

        Examples:
            | folder           | folder_delete           |
            | research-initial | ui_test_folder1_renamed |
            | research-initial | ui_test_folder2_renamed |
            | research-initial | ui_test_copy            |
            | research-initial | ui_test_empty_checksum1 |
            | research-initial | ui_test_empty_checksum2 |

    Scenario Outline: Multi-select moving files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user multi-select moves files / folders to <folder_new>
        Then user browses to subfolder <folder_new>
        And files / folders exist in <folder_new>
        And files / folders do not exist in <folder_new>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select copying files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <folder_new>
        And user multi-select copies files / folders to <folder>
        Then files / folders exist in <folder_new>
        And module "research" is shown
        And user browses to folder <folder>
        And files / folders exist in <folder>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select copying and overwriting files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <folder_new>
        And user multi-select copies overwrites files / folders to <folder>
        Then files / folders exist in <folder_new>
        And module "research" is shown
        And user browses to folder <folder>
        And files / folders exist in <folder>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select copying and overwriting all files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <folder_new>
        And user multi-select copies overwrites all files / folders to <folder>
        Then files / folders exist in <folder_new>
        And module "research" is shown
        And user browses to folder <folder>
        And files / folders exist in <folder>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select moving and overwriting files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user multi-select moves overwrites files / folders to <folder_new>
        Then user browses to subfolder <folder_new>
        And files / folders exist in <folder_new>
        And files / folders do not exist in <folder_new>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select copying files / folder 2
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <folder_new>
        And user multi-select copies files / folders to <folder>
        Then files / folders exist in <folder_new>
        And module "research" is shown
        And user browses to folder <folder>
        And files / folders exist in <folder>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select moving and overwriting all files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user multi-select moves overwrites all files / folders to <folder_new>
        Then user browses to subfolder <folder_new>
        And files / folders exist in <folder_new>
        And files / folders do not exist in <folder_new>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select copying files / folder 3
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <folder_new>
        And user multi-select copies files / folders to <folder>
        Then files / folders exist in <folder_new>
        And module "research" is shown
        And user browses to folder <folder>
        And files / folders exist in <folder>

        Examples:
            | folder           | folder_new |
            | research-initial | clone      |


    Scenario Outline: Multi-select deleting files / folder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user browses to subfolder <subfolder>
        And user multi-select deletes files / folders
        Then files / folders do not exist in <subfolder>

        Examples:
            | folder           | subfolder |
            | research-initial | clone     |


    Scenario Outline: Research download checksum report
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user open checksum report
        And downloads checksum report as <format>
        Then checksum report is downloaded as <format>

        Examples:
            | folder           | format |
            | research-initial | csv    |
            | research-initial | txt    |


    Scenario Outline: Go to group manager from research
        Given user datamanager is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user clicks go to group manager
        And correct row in tree is active for <group>

        Examples:
            | folder            | group             |
            | research-initial1 | research-initial1 |
