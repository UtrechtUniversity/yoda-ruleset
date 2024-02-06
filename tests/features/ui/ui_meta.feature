@ui
Feature: Meta UI

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And collection /tempZone/home/research-initial/folder space exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Save metadata
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder>
        And user opens metadata form
        And user fills in metadata form
        And user clicks save button
        Then metadata form is saved as yoda-metadata.json for folder <folder>

        Examples:
            | folder           |
            | research-initial |


    Scenario Outline: Save metadata subfolder
        Given user researcher is logged in
        And module "research" is shown
        When user browses to folder <folder1>
        When user browses to folder <folder2>
        And user opens metadata form
        And user fills in metadata form
        And user clicks save button
        Then metadata form is saved as yoda-metadata.json for folder <folder>

        Examples:
            | folder                        | folder1          | folder2      |
            | research-initial/folder space | research-initial | folder space |


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


    Scenario Outline: Script in path
        Given user researcher is logged in
        When the user navigates to <page>
        Then an error is shown that the path does not exist

        Examples:
            | page                                                                 |
            | /research/metadata/form?path=<script>alert(document.domain)</script> |
