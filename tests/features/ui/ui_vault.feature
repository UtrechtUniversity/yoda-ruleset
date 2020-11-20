Feature: Vault UI

    Scenario: Browsing to a folder in the vault space
          Given user "<user>" is logged in
          When module "vault" module is shown
          And user browses to data package "<data_package>"
          #Then content of sub-folder "<data_package>" is shown

          Examples:
            | user       | data_package   |
            | researcher | vault-initial  |
            | researcher | vault-initial1 |
