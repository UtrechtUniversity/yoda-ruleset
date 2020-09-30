Feature: Folder

    Examples:
        | folder                           |
        | /tempZone/home/research-initial1 |

    Scenario: Folder lock
        Given the Yoda folder lock API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "LOCKED"

    Scenario: Folder get locks
        Given the Yoda folder get locks API is queried with "<folder>"
        Then the response status code is "200"
        And folder locks contains "<folder>"

    Scenario: Folder unlock
        Given the Yoda folder unlock API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "FOLDER"

    Scenario: Folder submit
        Given the Yoda folder submit API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "SUBMITTED"

    Scenario: Folder unsubmit
        Given the Yoda folder unsubmit API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "FOLDER"

    Scenario: Folder resubmit after unsubmit
        Given the Yoda folder submit API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "SUBMITTED"

    Scenario: Folder reject
        Given the Yoda folder reject API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "REJECTED"

    Scenario: Folder resubmit after reject
        Given the Yoda folder submit API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "SUBMITTED"

    Scenario: Folder accept
        Given the Yoda folder accept API is queried with "<folder>"
        Then the response status code is "200"
        And folder "<folder>" status is "ACCEPTED"
