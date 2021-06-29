Feature: Research API locked

    Examples:
        | collection                      |
        | /tempZone/home/research-initial |

    Background:
        Given user "researcher" is authenticated
        And collection "<collection>" exists
        And "<collection>" is locked

    Scenario Outline: Research folder add in locked collection
        Given user "researcher" is authenticated
        And the Yoda research folder add API is queried with "<folder>" and "<collection>"
        Then the response status code is "400"
        And folder "<folder>" does not exists in "<collection>"

        Examples:
            | folder                 |
            | api_test_folder_locked |

    Scenario Outline: Research folder rename in locked collection
        Given user "researcher" is authenticated
        And the Yoda research folder rename API is queried with "<folder_old>", "<folder>" and "<collection>"
        Then the response status code is "400"
        And folder "<folder>" does not exists in "<collection>"

        Examples:
            | folder_old             | folder                         |
            | api_test_folder_locked | api_test_folder_locked_renamed |

    Scenario Outline: Research folder delete in locked collection
        Given user "researcher" is authenticated
        And the Yoda research folder delete API is queried with "<folder>" and "<collection>"
        Then the response status code is "400"

        Examples:
            | folder                  |
            | api_test_folder_locked  |

    Scenario Outline: Research file copy in locked collection
        Given user "researcher" is authenticated
        And the Yoda research file copy API is queried with "<file>", "<copy>" and "<collection>"
        Then the response status code is "400"
        And file "<file>" exists in "<collection>"
        And file "<copy>" does not exist in "<collection>"

        Examples:
            | file               | copy                      |
            | yoda-metadata.json | yoda-metadata_locked.json |

    Scenario Outline: Research file rename in locked collection
        Given user "researcher" is authenticated
        And the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"
        Then the response status code is "400"
        And file "<file>" exists in "<collection>"
        And file "<file_renamed>" does not exist in "<collection>"

        Examples:
            | file               | file_renamed              |
            | yoda-metadata.json | yoda-metadata_locked.json |

#    Scenario Outline: Research file upload in locked collection
#        Given user "researcher" is authenticated
#        And a file "<file>" is uploaded in "<folder>"
#        Then the response status code is "200"
#        And file "<file>" does not exist in "<collection>"
#
#        Examples:
#            | file                 | folder            |
#            | upload_test_file.txt | /research-initial |

    Scenario Outline: Research file delete in locked collection
        Given user "researcher" is authenticated
        And the Yoda research file delete API is queried with "<file>" and "<collection>"
        Then the response status code is "400"

        Examples:
            | file                       |
            | yoda-metadata_renamed.json |
            | upload_test_file.txt       |
