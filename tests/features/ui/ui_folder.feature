Feature: Folder UI

    Examples:
        | folder            |
        | research-initial1 |

    Scenario: Folder lock
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user locks the folder
        Then the folder status is "Locked"

    Scenario: Folder unlock
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user unlocks the folder
        Then the folder status is "Unlocked"

    Scenario: Folder submit
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user submits the folder
        Then the folder status is "Submitted"

    Scenario: Folder unsubmit
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user unsubmits the folder
        Then the folder status is "Unsubmitted"

    Scenario: Folder resubmit after unsubmit
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user submits the folder
        Then the folder status is "Submitted"

    Scenario: Folder reject
        Given user "datamanager" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user rejects the folder
        Then the folder status is "Rejected"

    Scenario: Folder resubmit after reject
        Given user "researcher" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user submits the folder
        Then the folder status is "Submitted"

    Scenario: Folder accept
        Given user "datamanager" is logged in
        And module "research" is shown
        When user browses to folder "<folder>"
        And user accepts the folder
        Then the folder status is "Accepted"
