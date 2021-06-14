Feature: INTAKE UI

    Scenario: Intake scan only and find datasets and unrecognized files
        Given user "datamanager" is logged in
        And module "intake" is shown
        When activate study "test"
        And total datasets is "0"
        When activate study "initial"
        And total datasets is "0"
        And unscanned files are present
        When scanned for datasets
        Then scan button is disabled
        When scanning for datasets is successful
        And total datasets is "3"
        And unrecognized files are present

        When click for details of first dataset row

        When add "COMMENTS" to comment field and press comment button 

        When check first dataset for locking
        And lock and unlock buttons are "enabled"
		
        When uncheck first dataset for locking
        And lock and unlock buttons are "disabled"

        When check all datasets for locking

        Then click lock button 
#        When wait for all datasets to be in locked state successfully


    Scenario: Intake reporting
        Given user "datamanager" is logged in
        And module "intake" is shown
		
        When open intake reporting area
        When check reporting result
        When export all data and download file
        When return to intake area
