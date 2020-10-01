Feature: Research API

    Scenario: Folder add
        Given the Yoda folder add API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder           | collection                      |
            | api_test_folder1 | /tempZone/home/research-initial |
            | api_test_folder2 | /tempZone/home/research-initial |

    Scenario: Folder rename
        Given the Yoda folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder_old       | folder                   | collection                      |
            | api_test_folder1 | api_test_folder1_renamed | /tempZone/home/research-initial |

    Scenario: Folder delete
        Given the Yoda folder delete API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" does not exists in "<collection>"

        Examples:
            | folder                   | collection                      |
            | api_test_folder1_renamed | /tempZone/home/research-initial |
            | api_test_folder2         | /tempZone/home/research-initial |
