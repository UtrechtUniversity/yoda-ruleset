Feature: Research API (locked)

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is locked


    Scenario Outline: Research folder add in locked collection
        Given user researcher is authenticated
        And the Yoda research folder add API is queried with <folder> and <collection>
        Then the response status code is "400"
        And folder <folder> does not exist in <collection>

        Examples:
            | collection                      | folder                 |
            | /tempZone/home/research-initial | api_test_folder_locked |


    Scenario Outline: Research folder rename in locked collection
        Given user researcher is authenticated
        And the Yoda research folder rename API is queried with <folder_old>, <folder> and <collection>
        Then the response status code is "400"
        And folder <folder> does not exist in <collection>

        Examples:
            | collection                      | folder_old             | folder                         |
            | /tempZone/home/research-initial | api_test_folder_locked | api_test_folder_locked_renamed |


    Scenario Outline: Research folder delete in locked collection
        Given user researcher is authenticated
        And the Yoda research folder delete API is queried with <folder> and <collection>
        Then the response status code is "400"

        Examples:
            | collection                      | folder                  |
            | /tempZone/home/research-initial | api_test_folder_locked  |


    Scenario Outline: Research file copy in locked collection
        Given user researcher is authenticated
        And the Yoda research file copy API is queried with <file>, <copy>, <copy_collection> and <collection>
        Then the response status code is "400"
        And file <file> exists in <collection>
        And file <copy> does not exist in <collection>

        Examples:
            | collection                      | file               | copy                    | copy_collection                 |
            | /tempZone/home/research-initial | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial |


    Scenario Outline: Research file rename in locked collection
        Given user researcher is authenticated
        And the Yoda research file rename API is queried with <file>, <file_renamed> and <collection>
        Then the response status code is "400"
        And file <file> exists in <collection>
        And file <file_renamed> does not exist in <collection>

        Examples:
            | collection                      | file               | file_renamed              |
            | /tempZone/home/research-initial | yoda-metadata.json | yoda-metadata_locked.json |


    Scenario Outline: Research file upload in locked collection
        Given user researcher is authenticated
        And a file <file> is uploaded in <folder>
        Then the response status code is "200"
        And file <file> does not exist in <collection>

        Examples:
            | collection                      | file                 | folder            |
            | /tempZone/home/research-initial | upload_test_file.txt | /research-initial |


    Scenario Outline: Research file delete in locked collection
        Given user researcher is authenticated
        And the Yoda research file delete API is queried with <file> and <collection>
        Then the response status code is "400"

        Examples:
            | collection                      | file                       |
            | /tempZone/home/research-initial | yoda-metadata_renamed.json |
            | /tempZone/home/research-initial | upload_test_file.txt       |
