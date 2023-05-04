@datarequest
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
