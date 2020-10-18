Feature: Resources API

    Scenario: Find all groups for all categories current user is datamanager of
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for all research groups of current datamanager
        Then the response status code is "200"
        And "<group>" for datamanager are found

        Examples:
            | user        | group             |
            | datamanager | research-initial  |

    Scenario: Collect storage data for a datamanager
        Given user "<user>" is authenticated
        And the Yoda resources API is queried by a datamanager for monthly storage data
	    Then the response status code is "200"
	    And monthly storage data for a datamanager is found

        Examples:
            | user        | 
			| datamanager | 

   Scenario: As a datamanager request montly based statistics for the categories under care which are meant to be used to be exported in a file
        Given user "<user>" is authenticated
        And the Yoda resources API is queried by a for statistics data to be used as a feed for an export file
	    Then the response status code is "200"
	    And storage data for export is found

        Examples:
            | user        |
			| datamanager | 

    Scenario: As rodsadmin collect monthly statistics
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for all monthly statistics
        Then the response status code is "200"
       	And rodsadmin monthly statistics is found

        Examples:
            | user           |
			| technicaladmin |

    Scenario: List of all resources and corresponding tier data.
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for all resources and tiers
        Then the response status code is "200"
        And list of resources and tiers is found

        Examples:
            | user           |
			| technicaladmin |

    Scenario: Request the tiername for a resource 
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for tier_name of "<resource_name>"
        Then the response status code is "200"
        And "<tier_name>" is found

        Examples:
            | user           | resource_name | tier_name |
            | technicaladmin | irodsResc     | Standard  |

    Scenario: Request all available tiers 
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for all available tiers
	    Then the response status code is "200"
	    And list with "<tier_name>" is found

        Examples:
            | user           | tier_name |
            | technicaladmin | Standard  |

    Scenario: Save tier for given resource
        Given user "<user>" is authenticated
        And the Yoda resources API is requested to save tier "<tier_name>" for resource "<resource_name>"
        Then the response status code is "200"
        And tier is saved successfully for resource

        Examples:
            | user           | resource_name | tier_name |
            | technicaladmin | irodsResc     | blabla3   |
  
    Scenario: Get user type for current user
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for usertype of current user
        Then the response status code is "200"
        And "<user_type>" is found

        Examples:
            | user       | user_type |
            | researcher | rodsuser  |

    Scenario: Get the research groups a user is member of
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for research groups of current user
        Then the response status code is "200"
        And "<research_group>" are found for current user

       Examples:
            | user        | research_group   |
            | researcher | research-initial |

    Scenario: Check whether current user is datamanager of group
        Given user "<user>" is authenticated
        And the Yoda resources API is queried to know if current user is datamanager
        Then the response status code is "200"
        And current user is found

        Examples:
            | user        |
            | datamanager |

    Scenario: Get a full year of monthly storage data starting from indicated month and look back one year
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for full year of monthly data for group "<group_name>" starting from month "<current_month>" backward
        Then the response status code is "200"
        And full year storage data is found

        Examples:
            | user        | group_name        | current_month | 
            | datamanager | research-initial  | 10            | 
