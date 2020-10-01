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

    Scenario: Research file copy
        Given the Yoda research file copy API is queried with "<file>", "<copy>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" exists in "<collection>"
        And file "<copy>" exists in "<collection>"

        Examples:
            | file               | copy                    | collection                       |
            | yoda-metadata.json | yoda-metadata_copy.json | /tempZone/home/research-initial1 |

    Scenario: Research file rename
        Given the Yoda research file rename API is queried with "<file>", "<file_renamed>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" does not exist in "<collection>"
        And file "<file_renamed>" exists in "<collection>"

        Examples:
            | file                    | file_renamed               | collection                       |
            | yoda-metadata_copy.json | yoda-metadata_renamed.json | /tempZone/home/research-initial1 |

    Scenario: Research file delete
        Given the Yoda research file delete API is queried with "<file>" and "<collection>"
        Then the response status code is "200"
        And file "<file>" does not exist in "<collection>"

        Examples:
            | file                       | collection                       |
            | yoda-metadata_renamed.json | /tempZone/home/research-initial1 |

    Scenario: Research collection details
        Given the Yoda research system metadata API is queried with "<collection>"
        Then the response status code is "200"

        Examples:
            | collection                      |
            | /tempZone/home/research-initial |

    Scenario: Research collection details
        Given the Yoda research collection details API is queried with "<collection>"
        Then the response status code is "200"

        Examples:
            | collection                      |
            | /tempZone/home/research-initial |
