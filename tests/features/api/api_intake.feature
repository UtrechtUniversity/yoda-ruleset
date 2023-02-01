@intake
Feature: Intake API

    Scenario Outline: Find all studies a user is involved with
        Given user <user> is authenticated
        And the Yoda intake list studies API is queried
        Then the response status code is "200"
        And study <study> is returned

        Examples:
            | user        | study   |
            | researcher  | initial |
            | researcher  | test    |
            | datamanager | initial |
            | datamanager | test    |


    Scenario Outline: Find all studies a user is datamanager of
        Given user <user> is authenticated
        And the Yoda intake list datamanager studies API is queried
        Then the response status code is "200"
        And study <study> is returned

        Examples:
            | user        | study   |
            | datamanager | initial |
            | datamanager | test |


    Scenario Outline: Get the total count of all files in a collection
        Given user <user> is authenticated
        And the Yoda intake count total files API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Get list of all unrecognized and unscanned files
        Given user <user> is authenticated
        And the Yoda intake list unrecognized files API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Get list of all datasets
        Given user <user> is authenticated
        And the Yoda intake list datasets API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Scan for and recognize datasets in study intake area
        Given user <user> is authenticated
        And the Yoda intake scan for datasets API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Lock dataset in study intake area
        Given user <user> is authenticated
        And dataset exists
        And the Yoda intake lock API is queried with dataset id and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Unlock dataset in study intake area
        Given user <user> is authenticated
        And dataset exists
        And the Yoda intake unlock API is queried with dataset id and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Get all details for a dataset
        Given user <user> is authenticated
        And dataset exists
        And the Yoda intake dataset get details API is queried with dataset id and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |


    Scenario Outline: Add a comment to a dataset
        Given user <user> is authenticated
        And dataset exists
        And the Yoda intake dataset add comment API is queried with dataset id, study id <study_id> and comment <comment>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id | comment |
            | datamanager | initial  | initial |
            | researcher  | initial  | initial |


    Scenario Outline: Get vault dataset related counts for reporting for a study
        Given user <user> is authenticated
        And the Yoda intake report vault dataset counts per study API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id   |
            | datamanager | initial    |


    Scenario Outline: Get aggregated vault dataset info for reporting for a study
        Given user <user> is authenticated
        And the Yoda intake report vault aggregated info API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id |
            | datamanager | initial  |


    Scenario Outline: Get vault data for export of a study
        Given user <user> is authenticated
        And the Yoda intake report export study data API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id |
            | datamanager | initial  |
