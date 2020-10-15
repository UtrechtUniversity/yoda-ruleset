Feature: Datarequest API

    Scenario: Datarequest browse
        Given user "researcher" is authenticated
        And the Yoda datarequest browse API is queried
        Then the response status code is "200"

    Scenario: Datarequest submit
        Given user "researcher" is authenticated
        And the Yoda datarequest submit API is queried with data
        Then the response status code is "200"

    Scenario: Datarequest get
        Given user "researcher" is authenticated
        And datarequest exists
        And the Yoda datarequest get API is queried with request id
        Then the response status code is "200"
        And request status is "SUBMITTED"

    Scenario: Datarequest preliminary review submit
        Given user "bodmember" is authenticated
        And datarequest exists
        And the Yoda datarequest preliminary review submit API is queried with request id
        Then the response status code is "200"
        And request status is "PRELIMINARY_ACCEPT"

    Scenario: Datarequest preliminary review get
        Given user "bodmember" is authenticated
        And datarequest exists
        And the Yoda datarequest preliminary review get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest datamanager review submit
        Given user "datamanager" is authenticated
        And datarequest exists
        And the Yoda datarequest datamanager review submit API is queried with request id
        Then the response status code is "200"
        And request status is "DATAMANAGER_ACCEPT"

    Scenario: Datarequest datamanager review get
        Given user "bodmember" is authenticated
        And datarequest exists
        And the Yoda datarequest datamanager review get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest assignment submit
        Given user "bodmember" is authenticated
        And datarequest exists
        And the datarequest assignment submit API is queried with request id
        Then the response status code is "200"
        And request status is "UNDER_REVIEW"

    Scenario: Datarequest assignment get
        Given user "bodmember" is authenticated
        And datarequest exists
        And the Yoda datarequest assignment get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest review submit
        Given user "dmcmember" is authenticated
        And datarequest exists
        And the datarequest review submit API is queried with request id
        Then the response status code is "200"
        And request status is "REVIEWED"

    Scenario: Datarequest reviews get
        Given user "bodmember" is authenticated
        And datarequest exists
        And the Yoda datarequest reviews get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest evaluation submit
        Given user "bodmember" is authenticated
        And datarequest exists
        And the datarequest evaluation submit API is queried with request id
        Then the response status code is "200"
        And request status is "APPROVED"

# 'api_datarequest_dta_post_upload_actions',
#    Scenario: Datarequest DTA post upload actions
#        Given datarequest exists
#        And the Yoda datarequest DTA post upload actions API is queried with request id
#        Then the response status code is "200"

# 'api_datarequest_signed_dta_post_upload_actions',
#    Scenario: Datarequest signed DTA post upload actions
#        Given datarequest exists
#        And the Yoda datarequest signed DTA post upload actions API is queried with request id
#        Then the response status code is "200"

# 'api_datarequest_data_ready'
#    Scenario: Datarequest DTA ready actions
#        Given datarequest exists
#        And the Yoda datarequest DTA ready API is queried with request id
#        Then the response status code is "200"

#    Scenario: Datarequest resubmit
#        Given the Yoda datarequest submit API is queried with <data> and <previous_request_id>
#        Then the response status code is "200"
