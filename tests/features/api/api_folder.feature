@api
Feature: Folder API

    Scenario Outline: Folder lock
        Given user researcher is authenticated
        And the Yoda folder lock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status |
            | /tempZone/home/research-core-0     | LOCKED |
            | /tempZone/home/research-default-1  | LOCKED |
            | /tempZone/home/research-core-1     | LOCKED |
            | /tempZone/home/research-default-2  | LOCKED |
            | /tempZone/home/research-core-2     | LOCKED |
            | /tempZone/home/research-default-3  | LOCKED |
            | /tempZone/home/research-epos-msl-0 | LOCKED |
            | /tempZone/home/research-epos-msl-1 | LOCKED |


    Scenario Outline: Folder get locks
        Given user researcher is authenticated
        And the Yoda folder get locks API is queried with <folder>
        Then the response status code is "200"
        And folder locks contains <folder>

        Examples:
            | folder                             |
            | /tempZone/home/research-core-0     |
            | /tempZone/home/research-default-1  |
            | /tempZone/home/research-core-1     |
            | /tempZone/home/research-default-2  |
            | /tempZone/home/research-core-2     |
            | /tempZone/home/research-default-3  |
            | /tempZone/home/research-epos-msl-0 |
            | /tempZone/home/research-epos-msl-1 |


    Scenario Outline: Folder unlock
        Given user researcher is authenticated
        And the Yoda folder unlock API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status |
            | /tempZone/home/research-core-0     | FOLDER |
            | /tempZone/home/research-default-1  | FOLDER |
            | /tempZone/home/research-core-1     | FOLDER |
            | /tempZone/home/research-default-2  | FOLDER |
            | /tempZone/home/research-core-2     | FOLDER |
            | /tempZone/home/research-default-3  | FOLDER |
            | /tempZone/home/research-epos-msl-0 | FOLDER |
            | /tempZone/home/research-epos-msl-1 | FOLDER |


    Scenario Outline: Folder submit
        Given user researcher is authenticated
        And metadata JSON exists in <folder>
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status    |
            | /tempZone/home/research-core-0     | SUBMITTED |
            | /tempZone/home/research-default-1  | SUBMITTED |
            | /tempZone/home/research-core-1     | SUBMITTED |
            | /tempZone/home/research-default-2  | SUBMITTED |
            | /tempZone/home/research-core-2     | SUBMITTED |
            | /tempZone/home/research-default-3  | SUBMITTED |
            | /tempZone/home/research-epos-msl-0 | SUBMITTED |
            | /tempZone/home/research-epos-msl-1 | SUBMITTED |


    Scenario Outline: Folder unsubmit
        Given user researcher is authenticated
        And the Yoda folder unsubmit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status |
            | /tempZone/home/research-core-0     | FOLDER |
            | /tempZone/home/research-default-1  | FOLDER |
            | /tempZone/home/research-core-1     | FOLDER |
            | /tempZone/home/research-default-2  | FOLDER |
            | /tempZone/home/research-core-2     | FOLDER |
            | /tempZone/home/research-default-3  | FOLDER |
            | /tempZone/home/research-epos-msl-0 | FOLDER |
            | /tempZone/home/research-epos-msl-1 | FOLDER |


    Scenario Outline: Folder resubmit after unsubmit
        Given user researcher is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status    |
            | /tempZone/home/research-core-0     | SUBMITTED |
            | /tempZone/home/research-default-1  | SUBMITTED |
            | /tempZone/home/research-core-1     | SUBMITTED |
            | /tempZone/home/research-default-2  | SUBMITTED |
            | /tempZone/home/research-core-2     | SUBMITTED |
            | /tempZone/home/research-default-3  | SUBMITTED |
            | /tempZone/home/research-epos-msl-0 | SUBMITTED |
            | /tempZone/home/research-epos-msl-1 | SUBMITTED |


    Scenario Outline: Folder reject
        Given user datamanager is authenticated
        And the Yoda folder reject API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status   |
            | /tempZone/home/research-core-0     | REJECTED |
            | /tempZone/home/research-default-1  | REJECTED |
            | /tempZone/home/research-core-1     | REJECTED |
            | /tempZone/home/research-default-2  | REJECTED |
            | /tempZone/home/research-core-2     | REJECTED |
            | /tempZone/home/research-default-3  | REJECTED |
            | /tempZone/home/research-epos-msl-0 | REJECTED |
            | /tempZone/home/research-epos-msl-1 | REJECTED |


    Scenario Outline: Folder resubmit after reject
        Given user researcher is authenticated
        And the Yoda folder submit API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status    |
            | /tempZone/home/research-core-0     | SUBMITTED |
            | /tempZone/home/research-default-1  | SUBMITTED |
            | /tempZone/home/research-core-1     | SUBMITTED |
            | /tempZone/home/research-default-2  | SUBMITTED |
            | /tempZone/home/research-core-2     | SUBMITTED |
            | /tempZone/home/research-default-3  | SUBMITTED |
            | /tempZone/home/research-epos-msl-0 | SUBMITTED |
            | /tempZone/home/research-epos-msl-1 | SUBMITTED |


    Scenario Outline: Folder accept
        Given user datamanager is authenticated
        And the Yoda folder accept API is queried with <folder>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                             | status   |
            | /tempZone/home/research-core-0     | ACCEPTED |
            | /tempZone/home/research-default-1  | ACCEPTED |
            | /tempZone/home/research-core-1     | ACCEPTED |
            | /tempZone/home/research-default-2  | ACCEPTED |
            | /tempZone/home/research-core-2     | ACCEPTED |
            | /tempZone/home/research-default-3  | ACCEPTED |
            | /tempZone/home/research-epos-msl-0 | ACCEPTED |
            | /tempZone/home/research-epos-msl-1 | ACCEPTED |


    Scenario Outline: Folder secured
        Given user datamanager is authenticated
        Then folder <folder> status is <status>

        Examples:
            | folder                             | status |
            | /tempZone/home/research-core-0     | FOLDER |
            | /tempZone/home/research-default-1  | FOLDER |
            | /tempZone/home/research-core-1     | FOLDER |
            | /tempZone/home/research-default-2  | FOLDER |
            | /tempZone/home/research-core-2     | FOLDER |
            | /tempZone/home/research-default-3  | FOLDER |
            | /tempZone/home/research-epos-msl-0 | FOLDER |
            | /tempZone/home/research-epos-msl-1 | FOLDER |


    Scenario Outline: Folder submit (move to vault)
        Given user researcher is authenticated
        And user creates a new folder <folder>
        And metadata JSON exists in <folder>
        And the Yoda folder submit API is queried with <folder> and <delete_research_copy>
        Then the response status code is "200"
        And folder <folder> status is <status>

        Examples:
            | folder                                       | delete_research_copy | status    |
            | /tempZone/home/research-core-0/move_to_vault | True                 | SUBMITTED |


    Scenario Outline: Folder accept (move to vault)
        Given user datamanager is authenticated
        And the Yoda folder accept API is queried with <folder>
        Then the response status code is "200"
        Then folder <folder> does not exist

        Examples:
            | folder                                       |
            | /tempZone/home/research-core-0/move_to_vault |
