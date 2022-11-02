Feature: Publication UI

    Scenario Outline: Publication of teclab datapackage and test landing page output
        Given user datamanager is logged in
        When all notifications are reset
        Given user is not logged in


    Scenario Outline: Researcher submits folder
        Given user researcher is logged in
        And all notifications are reset
        And module "research" is shown
        When user browses to folder <folder>
        And user submits the folder
        Then the folder status is "Submitted"

        Examples:
            | folder            |
            | research-teclab-0 |


    Scenario Outline: Datamanager accepts folder
        Given user datamanager is logged in
        When user checks and clears notifications for status "Submitted"
        And module "research" is shown
        When user browses to folder <folder>
        And user accepts the folder
        Then the folder status is "Accepted"

        Examples:
            | folder            |
            | research-teclab-0 |


    Scenario Outline: Researcher submits data package for publication
        Given user researcher is logged in
        When user checks and clears notifications for status "Accepted"
        And module "vault" is shown
        When user browses to data package in <vault>
        And user submits the data package for publication
        And user chooses new publication
        And user agrees with terms and conditions        
        Then the data package status is "Submitted for publication"

        Examples:
            | vault          |
            | vault-teclab-0 |


    Scenario Outline: Datamanager approves data package for publication
        Given user datamanager is logged in
        When user checks and clears notifications for status "Submitted for publication"
        And module "vault" is shown
        When user browses to data package in <vault>
        And user approves the data package for publication
        Then the data package status is "Approved for publication"
        And the data package status is "Published"

        Examples:
            | vault          |
            | vault-teclab-0 |


    Scenario Outline: Researcher checks research provenance
        Given user researcher is logged in
        When user checks and clears notifications for status "Approved for publication"
        And module "research" is shown
        When user browses to folder <folder>
        And user checks provenance info research


        Examples:
            | folder            |
            | research-teclab-0 |


    Scenario Outline: Researcher checks vault provenance
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user checks provenance info vault

        Examples:
            | vault          |
            | vault-teclab-0 |


    Scenario Outline: Researcher checks published landingpage
        Given user researcher is logged in
        And module "vault" is shown
        When user browses to data package in <vault>
        And user downloads file yoda-metadata.json
        And user opens landingpage through system metadata
        Then landingpage content matches yoda-metadata.json

        Examples:
            | vault          |
            | vault-teclab-0 |
