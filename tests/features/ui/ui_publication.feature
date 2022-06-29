Feature: Publication of geo data

    Scenario Outline: Publication of teclab datapackage and test landing page output
        Given user "datamanager" is logged in
        When all notifications are reset
        Given user is not logged in

        Given user "researcher" is logged in
        When all notifications are reset
        And module "research" is shown
        When user browses to folder "<folder>"
        And user submits the folder
        Then the folder status is "Submitted"
        Given user is not logged in

        Given user "datamanager" is logged in
        When user checks and clears notifications for status "Submitted"
        And module "research" is shown
        When user browses to folder "<folder>"
        And user accepts the folder
        Then the folder status is "Accepted"
        Given user is not logged in

        Given user "researcher" is logged in
        When user checks and clears notifications for status "Accepted"
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user submits the data package for publication
        Then the data package status is "Submitted for publication"
        Given user is not logged in

        Given user "datamanager" is logged in
        When user checks and clears notifications for status "Submitted for publication"
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user approves the data package for publication
        Then the data package status is "Approved for publication"
        Given user is not logged in

        Given user "researcher" is logged in
        When user checks and clears notifications for status "Approved for publication"		
        And module "research" is shown
        When user browses to folder "<folder>"
        And user checks provenance info research
        And module "vault" is shown
        When user browses to data package in "<vault>"
        And user checks provenance info vault
        Then the data package status is "Published"
        And user downloads relevant files of datapackage
        Then user opens landingpage through system metadata
        And user checks landingpage content 
		
    Examples:
        | folder            | vault          |  
        | research-teclab-0 | vault-teclab-0 |