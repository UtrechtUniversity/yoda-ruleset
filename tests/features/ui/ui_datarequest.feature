@ui @datarequest
Feature: Datarequest UI

    Scenario Outline: Datarequest submit
        Given user researcher is logged in
        And module "datarequest" is shown
        When user clicks submit data request button
        And user fills in draft data request submission form
        And user clicks on save as draft button
        And user fills in data request submission form
        And user clicks on submit button
        Then data request is created


    Scenario: Datarequest preliminary review submit
        Given user projectmanager is logged in
        And module "datarequest" is shown
        # When preliminary review submit


    Scenario: Datarequest datamanager review submit
        Given user datamanager is logged in
        And module "datarequest" is shown
        # When review submit


    Scenario: Datarequest assignment submit
        Given user projectmanager is logged in
        And module "datarequest" is shown
        # When assignment submit


    Scenario: Datarequest review submit
        Given user dacmember is logged in
        And module "datarequest" is shown
        # When assignment submit


    Scenario: Datarequest evaluation submit
        Given user projectmanager is logged in
        And module "datarequest" is shown
        # When evaluation submit


    Scenario: Datarequest preregistration submit
        Given user researcher is logged in
        And module "datarequest" is shown
        # When preregistration submit


    Scenario: Datarequest preregistration confirm
        Given user projectmanager is logged in
        And module "datarequest" is shown
        # When preregistration submit


    Scenario: Datarequest datamanager upload DTA
        Given user datamanager is logged in
        And module "datarequest" is shown
        # When datamanager upload DTA


    Scenario: Datarequest researcher upload signed DTA
        Given user researcher is logged in
        And module "datarequest" is shown
        # When researcher upload signed DTA


    Scenario: Datarequest datamanager data ready
        Given user datamanager is logged in
        And module "datarequest" is shown
        # When datamanager data ready
