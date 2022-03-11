Feature: Deposit UI

  Scenario: Deposit 2 datapackages (open/restricted)
    Given user "researcher" is logged in
    And module "deposit" is shown
	
	When user starts a new deposit
	And module "deposit" is shown

    Given user clicks new deposit
    Then upload data step is shown

    Given data file is uploaded to deposit
    Given "restricted" metadata is uploaded

    When user clicks on document data button
    Then document data step is shown

    When user goes to submission page
    And user accepts terms
    And user submits data
    And submission is confirmed


  Scenario: Use open search to get to open and restricted landing pages
    Given user "viewer" is logged in
    And module "deposit" is shown
	
    When user searcher for "Lazlo"
    And search results are shown
    And landingpage shows "restricted" access
    And all fields contain correct data
    And user copies identifier to clipboard
    And user clicks for map details

    When user searcher for "HARM"
    And search results are shown
    And landingpage shows "Open" access
    And all fields contain correct data
    And user copies identifier to clipboard
    And user clicks for map details
    And user clicks for data access with "HARM" in title

