Feature: Resources API


    Scenario: Get the research groups a user is member or datamanager of
        Given user "<user>" is authenticated
        And the Yoda resources API is queried for all research groups
        Then the response status code is "200"
        And "<group>" is found

        Examples:
            | user        | group             |
            | researcher  | research-initial  |
            | datamanager | research-initial  |

    Scenario: Get a full year of monthly storage data starting from current month and look back one year
        Given user "<user>" is authenticated
        And the Yoda resources full year group data API is queried with "<group>"
	    Then the response status code is "200"
	    And monthly storage data for group is found

        Examples:
            | user        | group             |
            | researcher  | research-initial  |
            | datamanager | research-initial  |

    Scenario: Collect storage stats of last month for categories
        Given user "<user>" is authenticated
        And the Yoda resources category stats API is queried
        Then the response status code is "200"
        And category statistics are found

        Examples:
            | user           |
            | technicaladmin |
            | datamanager    |

   Scenario: Collect storage stats for all twelve months based upon categories a user is datamanager of
        Given user "<user>" is authenticated
        And the Yoda resources monthly category stats API is queried
	    Then the response status code is "200"
	    And storage data for export is found

        Examples:
            | user           |
            | technicaladmin |
			| datamanager    |


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
            | user           | resource_name | tier_name   |
            | technicaladmin | irodsResc     | NonStandard |
            | technicaladmin | irodsResc     | Standard    |
