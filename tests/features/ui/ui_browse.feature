Feature: Browse UI

    Scenario: Browsing to a folder in the research space
        Given user "<user>" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        #Then content of sub-folder "<folder>" is shown

        Examples:
          | user       | folder            |
          | researcher | research-initial  |
          | researcher | research-initial1 |

    Scenario: Browsing to a folder in the vault space
          Given user "<user>" is logged in
          And module "vault" is shown
          When user browses to data package "<data_package>"
          #Then content of sub-folder "<data_package>" is shown

          Examples:
            | user       | data_package   |
            | researcher | vault-initial  |
            | researcher | vault-initial1 |
