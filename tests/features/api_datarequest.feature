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

    Scenario: Preliminary review submit
        Given datarequest exists
        And the Yoda datarequest preliminary review submit API is queried with request id
        Then the response status code is "200"
        And request status is "accepted_for_dm_review"

    Scenario: Datamanager review submit
        Given datarequest exists
        Given the Yoda datarequest datamanager review submit API is queried with request id
        Then the response status code is "200"
        And request status is "dm_accepted"

#    Scenario: Datarequest resubmit
#        Given the Yoda datarequest submit API is queried with <data> and <previous_request_id>
#        Then the response status code is "200"

#    Scenario: Datarequest get
#        Given the Yoda datarequest get API is queried with <request_id>
#        Then the response status code is "200"
#        And <request_json> and <request_status> is returned

#    Scenario: Preliminary review submit
#        Given the Yoda datarequest preliminary review submit API is queried with <data> and <request_id>
#        Then the response status is code "200"

#    Scenario: Preliminary review get
#        Given the Yoda datarequest preliminary review get API is queried with <request_id>
#        Then the response status code is "200"
#        And <preliminary_review_json> is returned


#    Scenario: Datamanager review get
#        Given the Yoda datarequest datamanager review get API is queried with <request_id>
#        Then the response status code is "200"
#        And <datamanager_review_json> is returned

#    Scenario: Assignment submit
#        Given the datarequest assignment submit API is queried with <data> and <request_id>
#        Then the response status code is "200"

#    Scenario: Assignment get
#        Given the datarequest assignment get API is queried with <request_id>
#        Then the response status code is "200"
#        And <assignment_json> is returned

#    Scenario: Review submit
#        Given the datarequest review submit API is queried with <data> and <request_id>
#        Then the response status code is "200"

#    Scenario: Reviews get
#        Given the datarequest reviews get API is queried with <request_id>
#        Then the response status code is "200"
#        And <reviews> is returned

#    Scenario: Evaluation submit
#        Given the datarequest evaluation submit API is queried with <data> and <request_id>
#        Then the response status code is "200"
