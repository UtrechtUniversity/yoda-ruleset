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
          | datamanager | research-core-1    |
          | datamanager | research-default-2 |


    Scenario Outline: Browsing to a folder in the vault space
          Given user <user> is logged in
          And module "vault" is shown
          When user browses to data package <data_package>
          #Then content of sub-folder <data_package> is shown

          Examples:
            | user        | data_package    |
            | researcher  | vault-core-1    |
            | researcher  | vault-default-2 |
            | datamanager | vault-core-1    |
            | datamanager | vault-default-2 |


    Scenario: Browsing to a non existing page
        Given user researcher is logged in
        When module "nonexisting" is shown
        Then the 404 error page is shown
