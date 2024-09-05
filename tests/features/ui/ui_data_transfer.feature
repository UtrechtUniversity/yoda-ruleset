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
        And user clicks on the iCommands docs page
        Then iCommands docs page is displayed

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User copies iCommands configuration
        Given user <user> is logged in
        When user opens the Data Transfer page
        And user clicks on iCommands copy button
        Then iCommands configuration is copied

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User downloads iCommands configuration file
        Given user <user> is logged in
        When user opens the Data Transfer page
        And user clicks on iCommands download button
        Then iCommands configuration file is downloaded as <format>

        Examples:
            | user           | format       |
            | researcher     | json         |
            | technicaladmin | json         |


    Scenario Outline: User clicks on the Gocommands docs page
        Given user <user> is logged in
        When user opens the Data Transfer page
        And user clicks on Gocommands tab
        And user clicks on the Gocommands docs page
        Then Gocommands docs page is displayed

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User copies Gocommands configuration
        Given user <user> is logged in
        When user opens the Data Transfer page
        And user clicks on Gocommands tab
        And user clicks on Gocommands copy button
        Then Gocommands configuration is copied

        Examples:
            | user           |
            | researcher     |
            | technicaladmin |


    Scenario Outline: User downloads Gocommands configuration file
        Given user <user> is logged in
        When user opens the Data Transfer page
        And user clicks on Gocommands tab
        And user clicks on Gocommands download button
        Then Gocommands configuration file is downloaded as <format>

        Examples:
            | user           | format      |
            | researcher     | yml         |
            | technicaladmin | yml         |
