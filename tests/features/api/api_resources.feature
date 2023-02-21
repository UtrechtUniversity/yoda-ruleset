Feature: Resources API

    Scenario Outline: Get the paginated research groups a user is member or datamanager of
        Given user <user> is authenticated
        And the Yoda resources browse group data API is queried
        Then the response status code is "200"
        And group <group> is found

        Examples:
            | user        | group             |
            | researcher  | research-initial  |
            | datamanager | research-initial  |


    Scenario Outline: Get paginated result when searching for one specific group
        Given user <user> is authenticated
        And the Yoda resources API is queried for a paginated range of research groups filtered on group <group>
        Then the response status code is "200"
        And group <group> is found
        And only 1 group is found

        Examples:
            | user        | group         |
            | researcher  | deposit-pilot |
            | datamanager | deposit-pilot |


    Scenario Outline: Get a full year of monthly storage data starting from current month and look back one year
        Given user <user> is authenticated
        And the Yoda resources full year group data API is queried with <group>
	    Then the response status code is "200"
	    And monthly storage data for group is found

        Examples:
            | user        | group             |
            | researcher  | research-initial  |
            | datamanager | research-initial  |


    Scenario Outline: Collect storage stats of last month for categories
        Given user <user> is authenticated
        And the Yoda resources category stats API is queried
        Then the response status code is "200"
        And category statistics are found

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |


   Scenario Outline: Collect storage stats for all twelve months based upon categories a user is datamanager of
        Given user <user> is authenticated
        And the Yoda resources monthly category stats API is queried
	    Then the response status code is "200"
	    And storage data for export is found

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |
