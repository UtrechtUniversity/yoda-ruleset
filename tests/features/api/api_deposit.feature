Feature: Deposit API

    Examples:
        | collection                      |
        | /tempZone/home/research-initial |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is unlocked

    Scenario: Deposit API path
        Given user "researcher" is authenticated
        And the Yoda deposit path API is queried
        Then the response status code is "200"

#    Scenario Outline: Deposit file upload
#        Given user "researcher" is authenticated
#        And a file "<file>" is uploaded in "<folder>"
#        Then the response status code is "200"
#        And file "<file>" exists in "<collection>"

#        Examples:
#            | file                 | folder            |
#            | upload_test_file.txt | /research-initial |
