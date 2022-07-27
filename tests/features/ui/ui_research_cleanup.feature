Feature: Research cleanup temporary files UI

  Scenario: Deposit open and restricted data package
    Given user <user> is logged in
    And module "research" is shown
    When user browses to folder <folder>

    Given "Thumbs.db" is uploaded to folder <folder>
    Given ".DS_Store" is uploaded to folder <folder>
    Given "._test1" is uploaded to folder <folder>
    Given "._test2" is uploaded to folder <folder>

    When user opens cleanup dialog
    And delete first file directly
    And confirm deletion of file
    Then successfully deleted and 3 remaining

    When check all remaining files
    And confirm deletion of all selected files
    Then dialog closed and successfully deleted message showing

    When user opens cleanup dialog
    Then no temporary files remaining

    Examples:
        | user        | folder             |
        | researcher  | research-default-2 |
