Feature: Research API

    Examples:
        | collection                      |
        | /tempZone/home/research-initial |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is unlocked

    Scenario Outline: Research folder add
        Given user "researcher" is authenticated
        And the Yoda research folder add API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder                      |
            | api_test_folder             |
            | api_test_copy               |
            | api_test_move               |
            | api_test_'`~!@#$%^&()+=[]{} |

    Scenario Outline: Research folder rename
        Given user "researcher" is authenticated
        And the Yoda research folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" exists in "<collection>"

        Examples:
            | folder_old       | folder                   |
            | api_test_folder  | api_test_folder_renamed |

    Scenario Outline: Research file copy
        Given user "researcher" is authenticated
        And the Yoda research file copy API is queried with "<file>", "<copy>", "<copy_collection>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"
        And file "<copy>" exists in "<copy_collection>"

        Examples:
            | file               | copy                    | copy_collection                               |
            | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial               |
            | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial/api_test_copy |

    Scenario Outline: Research file rename
        Given user "researcher" is authenticated
        And the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" does not exist in "<collection>"
        And file "<file_renamed>" exists in "<collection>"

        Examples:
            | file                    | file_renamed               |
            | yoda-metadata_copy.json | yoda-metadata_renamed.json |

    Scenario Outline: Research file move
        Given user "researcher" is authenticated
        And the Yoda research file move API is queried with "<file>", "<move_collection>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<move_collection>"
        And file "<file>" does not exist in "<collection>"

        Examples:
            | file                       | move_collection                               |
            | yoda-metadata_renamed.json | /tempZone/home/research-initial/api_test_move |

    Scenario Outline: Research file upload
        Given user "researcher" is authenticated
        And a file "<file>" is uploaded in "<folder>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"

        Examples:
            | file                 | folder                                        |
            | upload_test_file.txt | /research-initial                             |
            | upload_test_file.txt | /research-initial/api_test_'`~!@#$%^&()+=[]{} |

    Scenario Outline: Research file delete
        Given user "researcher" is authenticated
        And the Yoda research file delete API is queried with "<file>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" does not exist in "<collection>"

        Examples:
            | file                       |
            | upload_test_file.txt       |

    Scenario Outline: Research folder delete
        Given user "researcher" is authenticated
        And the Yoda research folder delete API is queried with "<folder>" and "<collection>"
        Then the response status code is "200"
        And folder "<folder>" does not exists in "<collection>"

        Examples:
            | folder                      |
            | api_test_folder_renamed     |
            | api_test_copy               |
            | api_test_move               |
            | api_test_'`~!@#$%^&()+=[]{} |
