@ui
Feature: Vault UI

    Scenario Outline: Vault submit
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for publication
        And user chooses new publication
        And user agrees with terms and conditions
        Then the data package status is "Submitted for publication"
        And provenance log includes "Submitted for publication"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault cancel
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user cancels publication of the data package
        Then the data package status is "Unpublished"
        And provenance log includes "Unpublished"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault submit after cancel
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for publication
        And user chooses new publication
        And user agrees with terms and conditions
        Then the data package status is "Submitted for publication"
        And provenance log includes "Submitted for publication"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault publication approve
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user approves the data package for publication
        Then the data package status is "Approved for publication"
        And provenance log includes "Approved for publication"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault publication published
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Published"
        And provenance log includes "Published"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault depublish publication
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user requests depublication of data package
        Then the data package status is "Depublication pending"
        And provenance log includes "Depublication pending"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault publication depublished
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Depublished"
        And provenance log includes "Depublished"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault republish publication
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user requests republication of data package
        Then the data package status is "Republication pending"
        And provenance log includes "Republication pending"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault publication republished
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then the data package status is "Published"
        And provenance log includes "Published"

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault view metadata form
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        Then core metadata is visible

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault view metadata form
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks metadata button
        Then metadata form is visible

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault view system metadata
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks system metadata icon
        Then system metadata is visible

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Vault view provenance information
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks provenance icon
        Then provenance information is visible

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Revoke read access to research group
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks action menu to revoke access
        Then action menu holds option to grant access to research group

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Grant read access to research group
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And clicks action menu to grant access
        Then action menu holds option to revoke access from research group

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Copy datapackage to research space
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks action menu to copy data package to research
        And user chooses research folder corresponding to <vault>
        And user presses copy package button
        #Then data package is copied to research area

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Check datapackage compliance with policy
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks clicks action menu to check compliance
        And user chooses policy
        Then compliance result is presented

        Examples:
            | vault          |
            | vault-initial1 |


    Scenario Outline: Go to research space
        Given user datamanager is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user clicks go to research
	    Then the research space of <vault> is shown

        Examples:
            | vault          |
            | vault-initial1 |
