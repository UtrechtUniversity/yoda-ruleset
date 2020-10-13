Feature: Datarequest API

    Scenario: Datarequest browse
        Given the Yoda datarequest browse API is queried
        Then the response status code is "200"

    Scenario: Datarequest submit
        Given the Yoda datarequest submit API is queried with data
        Then the response status code is "200"

    Scenario: Datarequest get
        Given datarequest exists
        And the Yoda datarequest get API is queried with request id
        Then the response status code is "200"
        And request status is "submitted"

    Scenario: Datarequest preliminary review submit
        Given datarequest exists
        And the Yoda datarequest preliminary review submit API is queried with request id
        Then the response status code is "200"
        And request status is "accepted_for_dm_review"

    Scenario: Datarequest reliminary review get
        Given datarequest exists
        And the Yoda datarequest preliminary review get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest datamanager review submit
        Given datarequest exists
        Given the Yoda datarequest datamanager review submit API is queried with request id
        Then the response status code is "200"
        And request status is "dm_accepted"

    Scenario: Datarequest datamanager review get
        Given datarequest exists
        And the Yoda datarequest datamanager review get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest assignment submit
        Given datarequest exists
        And the datarequest assignment submit API is queried with request id
        Then the response status code is "200"
        And request status is "assigned"

    Scenario: Datarequest assignment get
        Given datarequest exists
        And the Yoda datarequest assignment get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest review submit
        Given datarequest exists
        And the datarequest review submit API is queried with request id
        Then the response status code is "200"
        And request status is "reviewed"

    Scenario: Datarequest reviews get
        Given datarequest exists
        And the Yoda datarequest reviews get API is queried with request id
        Then the response status code is "200"

    Scenario: Datarequest evaluation submit
        Given datarequest exists
        Given the datarequest evaluation submit API is queried with request id
        Then the response status code is "200"

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
