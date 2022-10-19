Feature: Group UI

    Scenario Outline: A datamanager imports group definitions through uploading a CSV file
        Given user datamanager is logged in
        And module "group_manager" is shown
        When user opens group import dialog
        And user clicks upload button
        And user clicks allow updates checkbox
        And user clicks allow deletions checkbox
        Then process csv and check number of rows
        And click on imported row 0 and check group properties
        And find groupmember "manager@uu.nl"
        And user opens group import dialog
        And click on imported row 1 and check group properties
        And find groupmember "member1@uu.nl"