Feature: Research API

    Background:
        Given user researcher is authenticated
        And collection /tempZone/home/research-initial exists
        And /tempZone/home/research-initial is unlocked


    Scenario Outline: Research folder add
        Given user researcher is authenticated
        And the Yoda research folder add API is queried with <folder> and <collection>
        Then the response status code is "200"
        And folder <folder> exists in <collection>

        Examples:
            | collection                      | folder                      |
            | /tempZone/home/research-initial | api_test_folder             |
            | /tempZone/home/research-initial | api_test_copy               |
            | /tempZone/home/research-initial | api_test_move               |
            | /tempZone/home/research-initial | api_test_1234567890         |


    Scenario Outline: Research folder copy
        Given user researcher is authenticated
        And the Yoda research folder copy API is queried with <folder>, <copy>, and <collection>
        Then the response status code is "200"
        And folder <folder> exists in <collection>
        And folder <copy> exists in <collection>

        Examples:
            | collection                      | folder             | copy                    |
            | /tempZone/home/research-initial | api_test_copy      | api_test_copy2          |
            | /tempZone/home/research-initial | api_test_copy      | api_test_move1          |


    Scenario Outline: Research folder move
        Given user researcher is authenticated
        And the Yoda research folder move API is queried with <folder>, <move>, and <collection>
        Then the response status code is "200"
        And folder <folder> does not exist in <collection>
        And folder <move> exists in <collection>

        Examples:
            | collection                      | folder             | move                |
            | /tempZone/home/research-initial | api_test_move1     | api_test_move2      |


    Scenario Outline: Research folder rename
        Given user researcher is authenticated
        And the Yoda research folder rename API is queried with <folder_old>, <folder> and <collection>
        Then the response status code is "200"
        And folder <folder_old> does not exist in <collection>
        And folder <folder> exists in <collection>

        Examples:
            | collection                      | folder_old       | folder                  |
            | /tempZone/home/research-initial | api_test_folder  | api_test_folder_renamed |


    Scenario Outline: Research file copy
        Given user researcher is authenticated
        And the Yoda research file copy API is queried with <file>, <copy>, <copy_collection> and <collection>
        Then the response status code is "200"
        And file <file> exists in <collection>
        And file <copy> exists in <copy_collection>

        Examples:
            | collection                      | file               | copy                    | copy_collection                               |
            | /tempZone/home/research-initial | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial               |
            | /tempZone/home/research-initial | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial/api_test_copy |


    Scenario Outline: Research file rename
        Given user researcher is authenticated
        And the Yoda research file rename API is queried with <file>, <file_renamed> and <collection>
        Then the response status code is "200"
        And file <file> does not exist in <collection>
        And file <file_renamed> exists in <collection>

        Examples:
            | collection                      | file                    | file_renamed               |
            | /tempZone/home/research-initial | yoda-metadata_copy.json | yoda-metadata_renamed.json |


    Scenario Outline: Research file move
        Given user researcher is authenticated
        And the Yoda research file move API is queried with <file>, <move_collection> and <collection>
        Then the response status code is "200"
        And file <file> exists in <move_collection>
        And file <file> does not exist in <collection>

        Examples:
            | collection                      | file                       | move_collection                               |
            | /tempZone/home/research-initial | yoda-metadata_renamed.json | /tempZone/home/research-initial/api_test_move |


    Scenario Outline: Research file upload
        Given user researcher is authenticated
        And a file <file> is uploaded in <folder>
        Then the response status code is "200"
        And file <file> exists in <collection>

        Examples:
            | collection                      | file                 | folder                                        |
            | /tempZone/home/research-initial | upload_test_file.txt | /research-initial                             |
            | /tempZone/home/research-initial | upload_test_file.txt | /research-initial/api_test_1234567890         |


    Scenario Outline: Research file delete
        Given user researcher is authenticated
        And the Yoda research file delete API is queried with <file> and <collection>
        Then the response status code is "200"
        And file <file> does not exist in <collection>

        Examples:
            | collection                      | file                 |
            | /tempZone/home/research-initial | upload_test_file.txt |


    Scenario Outline: Research folder delete
        Given user researcher is authenticated
        And the Yoda research folder delete API is queried with <folder> and <collection>
        Then the response status code is "200"
        And folder <folder> does not exist in <collection>

        Examples:
            | collection                      | folder                  |
            | /tempZone/home/research-initial | api_test_folder_renamed |
            | /tempZone/home/research-initial | api_test_copy           |
            | /tempZone/home/research-initial | api_test_copy2          |
            | /tempZone/home/research-initial | api_test_move           |
            | /tempZone/home/research-initial | api_test_move2          |
            | /tempZone/home/research-initial | api_test_1234567890     |


    Scenario Outline: Research manifest
        Given user researcher is authenticated
        And the Yoda research manifest API is queried with <collection>
        Then the response status code is "200"
        And checksum manifest is returned

        Examples:
            | collection                      |
            | /tempZone/home/research-initial |
