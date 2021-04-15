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

    Scenario: Vault publication approve
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user approves the data package for publication
        Then the data package status is "Approved for publication"

    Scenario: Vault depublish publication
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user waits for status "Published"  ????????????????????
        And user approves the data package for depublication
        Then the data package status is "Depublication pending"

    Scenario: Vault republish publication
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user waits for status "Depublished" ?????????????????????
        And user selects republication
        Then the data package status is "Republication pending"

    Scenario: Vault views metadata form [LAATSTE STAP NOG]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks metatadata button
        Then metadata form is visible

    Scenario: Views system metadata [OK]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks system metadata icon
        Then system metadata is visible

    Scenario: Views provenance information [OK]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks provenance icon # actionlog-icon
        Then provenance information is visible

#####
    Scenario: Revoke read access to research group ## [OK]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And clicks action menu to revoke access
        Then action menu holds option to grant access to research group #dropdown-item action-grant-vault-access

    Scenario: Grant read access to research group ## [OK]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And clicks action menu to grant access
        Then action menu holds option to revoke access from research group

####
    Scenario: Copy datapackage to research space [Laatste stap]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks action menu to go to research
        And user chooses research folder corresponding to "<vault>"
        And user presses copy package button
        Then package is copied to research area

####
    Scenario: Check datapackage compliancy with policy [OK]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks clicks action menu to check compliancy
        And user chooses policy
        Then compliancy result is presented

####
    Scenario: Go to research environment [laatste stap]
        Given user "datamanager" is logged in
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user clicks action menu go to research
        Then module "research" is shown
