@api @intake
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
            | datamanager | test    |


    Scenario Outline: Get the total count of all files in a collection
        Given user <user> is authenticated
        And the Yoda intake count total files API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        |
            | datamanager | /tempZone/home/grp-intake-initial |
            | researcher  | /tempZone/home/grp-intake-initial |


    Scenario Outline: Get list of all unrecognized and unscanned files
        Given user <user> is authenticated
        And the Yoda intake list unrecognized files API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        |
            | datamanager | /tempZone/yoda/grp-intake-initial |
            | researcher  | /tempZone/yoda/grp-intake-initial |


    Scenario Outline: Get list of all datasets
        Given user <user> is authenticated
        And the Yoda intake list datasets API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        |
            | datamanager | /tempZone/home/grp-intake-initial |
            | researcher  | /tempZone/home/grp-intake-initial |


    Scenario Outline: Scan for and recognize datasets in study intake area
        Given user <user> is authenticated
        And the Yoda intake scan for datasets API is queried with collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        |
            | datamanager | /tempZone/home/grp-intake-initial |
            | researcher  | /tempZone/home/grp-intake-initial |


    Scenario Outline: Lock dataset in study intake area
        Given user <user> is authenticated
        And the Yoda intake lock API is queried with dataset id <dataset_id> and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        | dataset_id              |
            | datamanager | /tempZone/home/grp-intake-initial | 3y*discount*B00000*Raw  |
            | researcher  | /tempZone/home/grp-intake-initial | 3y*discount*B00001*Raw  |


    Scenario Outline: Cannot lock non-existent dataset
        Given user <user> is authenticated
        And the Yoda intake lock API is queried with dataset id <dataset_id> and collection <collection>
        # Errors during locking individual datasets do not result in an error status code. This test
        # codifies current behaviour of this API endpoint.
        Then the response status code is "200"
        And the result is equivalent to {"error_dataset_ids": ["3y\ndiscount\nB99999\nRaw"], "error_msg": "Something went wrong locking datasets", "proc_status": "NOK"}

        Examples:
            | user        | collection                        | dataset_id             |
            | datamanager | /tempZone/home/grp-intake-initial | 3y*discount*B99999*Raw |


    Scenario Outline: Unlock dataset in study intake area
        Given user <user> is authenticated
        And the Yoda intake unlock API is queried with dataset id <dataset_id> and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                        | dataset_id             |
            | datamanager | /tempZone/home/grp-intake-initial | 3y*discount*B00000*Raw |
            | researcher  | /tempZone/home/grp-intake-initial | 3y*discount*B00001*Raw |


    Scenario Outline: Cannot unlock non-existent dataset
        Given user <user> is authenticated
        And the Yoda intake unlock API is queried with dataset id <dataset_id> and collection <collection>
        # Errors during unlocking individual datasets do not result in an error status code. This test
        # codifies current behaviour of this API endpoint.
        Then the response status code is "200"
        And the result is equivalent to {"error_dataset_ids": ["3y\ndiscount\nB99999\nRaw"], "error_msg": "Something went wrong unlocking datasets", "proc_status": "NOK"}

        Examples:
            | user        | collection                        | dataset_id             |
            | datamanager | /tempZone/home/grp-intake-initial | 3y*discount*B99999*Raw |


    Scenario Outline: Get all details for a dataset
        Given user <user> is authenticated
        And the Yoda intake dataset get details API is queried with dataset id <dataset_id> and collection <collection>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                             | dataset_id              |
            | datamanager | /tempZone/home/grp-intake-initial      | 3y*discount*B00000*Raw  |
            | researcher  | /tempZone/home/grp-intake-initial      | 3y*discount*B00001*Raw  |


    Scenario Outline: Add a comment to a dataset
        Given user <user> is authenticated
        And the Yoda intake dataset add comment API is queried with dataset id <dataset_id>, study id <study_id> and comment <comment>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id            | comment  | dataset_id             |
            | datamanager | grp-intake-initial  | comment1 | 3y*discount*B00000*Raw |
            | researcher  | grp-intake-initial  | comment2 | 3y*discount*B00001*Raw |


    Scenario Outline: Cannot add comment to nonexistent dataset
        Given user <user> is authenticated
        And the Yoda intake dataset add comment API is queried with dataset id <dataset_id>, study id <study_id> and comment <comment>
        # Adding a comment to a nonexistent dataset currently does not result in an error status code. This test
        # codifies current behaviour of this API endpoint.
        Then the response status code is "200"
        And the result is equivalent to {"error_msg": "Dataset does not exist", "proc_status": "NOK"}

        Examples:
            | user        | study_id            | comment  | dataset_id             |
            | datamanager | grp-intake-initial  | comment1 | 3y*discount*B99999*Raw |


    Scenario Outline: Get vault dataset related counts for reporting for a study
        Given user <user> is authenticated
        And the Yoda intake report vault dataset counts per study API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id              |
            | datamanager | grp-intake-initial    |


    Scenario Outline: Get aggregated vault dataset info for reporting for a study
        Given user <user> is authenticated
        And the Yoda intake report vault aggregated info API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id            |
            | datamanager | grp-intake-initial  |


    Scenario Outline: Get vault data for export of a study
        Given user <user> is authenticated
        And the Yoda intake report export study data API is queried with study id <study_id>
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id            |
            | datamanager | grp-intake-initial  |
