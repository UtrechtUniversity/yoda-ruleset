Feature: INTAKE UI

    Examples:
        | study   |
        | initial |

# PREREQUISITE: NO DATASETS HAVE BEEN ADDED YET

 #   WE GAAN UIT VAN STUDY INITIAL!

    Scenario 1: Intake scan only and find datasets and unrecognized files
        Given user "datamanager" is logged in
        And module "intake" is shown
		# And activate "<study>" - hierin switchen als niet actief is
		
#        And total datasets is "0"   OK
#	    And unscanned files are present  OK => test bestanden door ANSIBLE geplaatst
#		When scanned for datasets OK
#        Then scan button is disabled OK#
#		And scanning for datasets is successfull
#		# scanning starts,takes a while
		## WAIT??s
#        And datasets are present
#		And unrecognized files are present
#        And click for details of first dataset row
#		And add "COMMENTS" to comment field and press comment button 

#		And check first dataset for locking
#		And lock and unlock buttons are "enabled"
		
#		And uncheck first dataset for locking
#		And lock and unlock buttons are "disabled"

#        And check all datasets for locking

#        Then click lock button 
#		And wait for all datasets to be in locked state successfully
		
        # NU gaat het vanzelf


#    Scenario 2: Intake reporting
#        Given user "datamanager" is logged in
#        And module "intake" is shown
		
#		And open intake reporting area
#		And check reporting result
#        And export all data and download file
#		And return to intake area