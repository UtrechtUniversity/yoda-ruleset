@ui
Feature: Data Transfer UI

    Scenario Outline: Data Transfer page
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then Data Transfer is shown

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User clicks on the iCommands docs page
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then user clicks on the iCommands docs page

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User copies iCommands configuration
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then user clicks on iCommands copy button

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User downloads iCommands configuration file
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then user clicks on iCommands download button and configuration file is downloaded as <format>

        Examples:
            | user           | format       |
            | researcher     | json         |
            | technicaladmin | json         |


    Scenario Outline: User clicks on the Gocommands docs page
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then  user clicks on Gocommands tab
        Then user clicks on the Gocommands docs page

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User copies Gocommands configuration
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then user clicks on Gocommands tab
        Then user clicks on Gocommands copy button

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User downloads Gocommands configuration file
        Given user <user> is logged in
        When user opens the Data Transfer page
        Then user clicks on Gocommands tab
        Then user clicks on Gocommands download button and configuration file is downloaded as <format>

        Examples:
            | user           | format      |
            | researcher     | yml         |
            | technicaladmin | yml         |
