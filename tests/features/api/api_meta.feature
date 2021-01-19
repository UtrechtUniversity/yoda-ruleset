Feature: Meta API

    Scenario: Meta clone file
        Given user "researcher" is authenticated
        And metadata JSON exists in "<collection>"
        And subcollection "<target_coll>" exists
        And the Yoda meta clone file API is queried with "<target_coll>"
        Then the response status code is "200"
        And metadata JSON is cloned into "<target_coll>"

        Examples:
            | collection                      | target_coll                           |
            | /tempZone/home/research-initial | /tempZone/home/research-initial/clone |

    Scenario: Meta remove
        Given user "researcher" is authenticated
        And metadata JSON exists in "<collection>"
        And the Yoda meta remove API is queried with metadata and "<collection>"
        Then the response status code is "200"
        And metadata JSON is removed from "<collection>"

        Examples:
            | collection                            |
            | /tempZone/home/research-initial/clone |
            | /tempZone/home/research-initial       |
