Feature: Meta API

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Meta clone file
        Given user researcher is authenticated
        And metadata JSON exists in <collection>
        And subcollection <target_coll> exists
        And the Yoda meta clone file API is queried with <target_coll>
        Then the response status code is "200"
        And metadata JSON is cloned into <target_coll>

        Examples:
            | collection                      | target_coll                           |
            | /tempZone/home/research-initial | /tempZone/home/research-initial/clone |


    Scenario Outline: Meta remove
        Given user researcher is authenticated
        And cloned metadata JSON exists in <clone_collection>
        And the Yoda meta remove API is queried with metadata and <clone_collection>
        Then the response status code is "200"
        And metadata JSON is removed from <clone_collection>

        Examples:
            | clone_collection                      |
            | /tempZone/home/research-initial/clone |
