Feature: Folder API

    Examples:
        | folder                            |
        | /tempZone/home/research-core-0    |
        | /tempZone/home/research-default-1 |
        | /tempZone/home/research-core-1    |
        | /tempZone/home/research-default-2 |


    Scenario: Folder lock
        Given user researcher is authenticated
        And the Yoda folder lock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status |
            | LOCKED |


    Scenario: Folder get locks
        Given user researcher is authenticated
        And the Yoda folder get locks API is queried with <folder>
        Then the response status code is "200"
        And folder locks contains <folder>


    Scenario: Folder unlock
        Given user researcher is authenticated
        And the Yoda folder unlock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status |
            | FOLDER |


    Scenario: Folder submit
        Given user researcher is authenticated
        And metadata JSON exists in <folder>
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status    |
            | SUBMITTED |


    Scenario: Folder unsubmit
        Given user researcher is authenticated
        And the Yoda folder unsubmit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status |
            | FOLDER |


    Scenario: Folder resubmit after unsubmit
        Given user researcher is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status    |
            | SUBMITTED |


    Scenario: Folder reject
        Given user datamanager is authenticated
        And the Yoda folder reject API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status   |
            | REJECTED |


    Scenario: Folder resubmit after reject
        Given user researcher is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status    |
            | SUBMITTED |


    Scenario: Folder accept
        Given user datamanager is authenticated
        And the Yoda folder accept API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | status   |
            | ACCEPTED |
