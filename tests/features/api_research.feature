Feature: Research API

    Scenario: Research folder add
        Given the Yoda research folder add API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder           | collection                      |
            | api_test_folder1 | /tempZone/home/research-initial |
            | api_test_folder2 | /tempZone/home/research-initial |

    Scenario: Research folder rename
        Given the Yoda research folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder_old       | folder                   | collection                      |
            | api_test_folder1 | api_test_folder1_renamed | /tempZone/home/research-initial |

    Scenario: Research folder delete
        Given the Yoda research folder delete API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" does not exists in "<collection>"

        Examples:
            | folder                   | collection                      |
            | api_test_folder1_renamed | /tempZone/home/research-initial |
            | api_test_folder2         | /tempZone/home/research-initial |

    Scenario: Research collection details
        Given the Yoda research collection details API is queried with "<collection>"
        Then the response status code is "200"

        Examples:
            | collection                      |
            | /tempZone/home/research-initial |
