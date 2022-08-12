Feature: Meta form API

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Meta form save
        Given user researcher is authenticated
        And the Yoda meta form save API is queried with metadata and <collection>
        Then the response status code is "200"
        And file <file> exists in <collection>

        Examples:
            | collection                       | file               |
            | /tempZone/home/research-initial  | yoda-metadata.json |
            | /tempZone/home/research-initial1 | yoda-metadata.json |


    Scenario Outline: Meta form save long content
        Given user researcher is authenticated
        And the Yoda meta form save API is queried with long metadata and <collection>
        Then the response status code is "200"
        And file <file> exists in <collection>

        Examples:
            | collection                       | file               |
            | /tempZone/home/research-initial  | yoda-metadata.json |
            | /tempZone/home/research-initial1 | yoda-metadata.json |


    Scenario Outline: Meta form load
        Given user researcher is authenticated
        And the Yoda meta form load API is queried with <collection>
        Then the response status code is "200"
        And metadata is returned for <collection>

        Examples:
            | collection                       |
            | /tempZone/home/research-initial  |
            | /tempZone/home/research-initial1 |


    Scenario Outline: Meta form save in vault
        Given user datamanager is authenticated
        And data package exists in <vault>
        And the Yoda meta form save API is queried with metadata on datapackage in <vault>
        Then the response status code is "200"

        Examples:
            | vault                          |
            | /tempZone/home/vault-core-0    |
            | /tempZone/home/vault-default-1 |
            | /tempZone/home/vault-core-1    |
            | /tempZone/home/vault-default-2 |
