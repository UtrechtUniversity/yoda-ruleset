Feature: Vault UI

    Examples:
        | vault          |
        | vault-initial1 |

    Scenario: Vault submit
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for publication
        Then the data package status is "Submitted for publication"
        And provenance log includes "Submitted for publication"

    Scenario: Vault cancel
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user cancels publication of the data package
        Then the data package status is "Unpublished"
        And provenance log includes "Unpublished"

    Scenario: Vault submit after cancel
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for publication
        Then the data package status is "Submitted for publication"
        And provenance log includes "Submitted for publication"

    Scenario: Vault publication approve
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user approves the data package for publication
        Then the data package status is "Approved for publication"
        And provenance log includes "Approved for publication"

    Scenario: Vault publication published
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Published"
        And provenance log includes "Published"

    Scenario: Vault depublish publication
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user requests depublication of data package
        Then the data package status is "Depublication pending"
        And provenance log includes "Depublication pending"

    Scenario: Vault publication depublished
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Depublished"
        And provenance log includes "Depublished"

    Scenario: Vault republish publication
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user requests republication of data package
        Then the data package status is "Republication pending"
        And provenance log includes "Republication pending"

    Scenario: Vault publication republished
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Published"
        And provenance log includes "Published"

    Scenario: Vault view metadata form
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then core metadata is visible

    Scenario: Vault view metadata form
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks metatadata button
        Then metadata form is visible

    Scenario: Vault view system metadata
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks system metadata icon
        Then system metadata is visible

    Scenario: Vault view provenance information
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks provenance icon
        Then provenance information is visible

    Scenario: Revoke read access to research group
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks action menu to revoke access
        Then action menu holds option to grant access to research group

    Scenario: Grant read access to research group
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And clicks action menu to grant access
        Then action menu holds option to revoke access from research group

    Scenario: Copy datapackage to research space
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks action menu to copy data package to research
        And user chooses research folder corresponding to <vault>
        And user presses copy package button
        #Then data package is copied to research area

    Scenario: Check datapackage compliancy with policy
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks clicks action menu to check compliancy
        And user chooses policy
        Then compliancy result is presented

    Scenario: Go to research space
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks action menu go to research
	    Then the research space of <vault> is shown

    Scenario: Go to search page, find open datapackage, view landingpage and have access to data
        Given user researcher is logged in
        And module "search" is shown
        When user searches for "geo"
        And user clicks first open search result
        Then open datapackage details are visible
        When user clicks for map details
        Then map is shown
        When user clicks to copy reference
        Then reference confirmation is shown
        When user clicks for data access
        Then vault browser is shown
