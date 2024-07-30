@ui
Feature: Browse UI

    Scenario Outline: Browsing to a folder in the research space
        Given user <user> is logged in
        And module "research" is shown
        When user browses to folder <folder>
        #Then content of sub-folder <folder> is shown

        Examples:
          | user        | folder             |
          | researcher  | research-core-1    |
          | researcher  | research-default-2 |
          | researcher  | research-core-2    |
          | researcher  | research-default-3 |
          | datamanager | research-core-1    |
          | datamanager | research-default-2 |
          | datamanager | research-core-2    |
          | datamanager | research-default-3 |


    Scenario Outline: Browsing to a folder in the vault space
          Given user <user> is logged in
          And module "vault" is shown
          When user browses to folder <folder>
          #Then content of sub-folder <folder> is shown

          Examples:
            | user        | folder          |
            | researcher  | vault-core-1    |
            | researcher  | vault-default-2 |
            | researcher  | vault-core-2    |
            | researcher  | vault-default-3 |
            | datamanager | vault-core-1    |
            | datamanager | vault-default-2 |
            | datamanager | vault-core-2    |
            | datamanager | vault-default-3 |


    Scenario Outline: Cannot click to view files do not have access to
        Given user technicaladmin is logged in
        And module "research" is shown
        When user browses to folder <folder>
        Then there is no link to <file> in folder <folder>

        Examples:
          | folder           | file               |
          | research-initial | yoda-metadata.json |
    

    Scenario Outline: Cannot click to view large files
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder1>
        When user browses to folder <folder2>
        Then there is no link to <file> in folder <folder>

        Examples:
          | user       | folder                    | folder1          | folder2  | file            |
          | researcher | research-initial/testdata | research-initial | testdata | large-file.html |


    Scenario: Browsing to a non existing page
        Given user researcher is logged in
        When module "nonexisting" is shown
        Then the 404 error page is shown
