Feature: Meta UI

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Save metadata
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user opens metadata form
        And users fills in metadata form
        And users clicks save button
        Then metadata form is saved as yoda-metadata.json

        Examples:
            | folder           |
            | research-initial |


    Scenario Outline: Delete metadata
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user opens metadata form
        And users clicks delete all metadata button
        Then metadata is deleted from folder

        Examples:
            | folder           |
            | research-initial |


    Scenario Outline: Check person identifier functionality in metadata form
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user opens metadata form
        And users checks person identifier field in metadata form

        Examples:
            | folder             |
            | research-default-3 |
