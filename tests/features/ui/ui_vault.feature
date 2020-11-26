Feature: Vault UI

    Examples:
        | vault          |
        | vault-initial1 |

    Scenario: Vault submit
        Given user "researcher" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user submits the data package for publication
        Then the data package status is "Submitted for publication"

    Scenario: Vault cancel
        Given user "researcher" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user cancels publication of the data package
        Then the data package status is "Unpublished"

    Scenario: Vault submit after cancel
        Given user "researcher" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user submits the data package for publication
        Then the data package status is "Submitted for publication"

    Scenario: Vault approve
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user approves the data package for publication
        Then the data package status is "Approved for publication"
