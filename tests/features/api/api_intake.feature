@intake
Feature: Intake API

    Scenario: Find all studies a user is involved with
        Given user "<user>" is authenticated
        And the Yoda intake list studies API is queried
        Then the response status code is "200"
        And study "<study>" is returned

        Examples:
            | user        | study   |
            | researcher  | initial |
            | researcher  | test    |
            | datamanager | initial |
            | datamanager | test    |

    Scenario: Find all studies a user is datamanager of
        Given user "<user>" is authenticated
        And the Yoda intake list datamanager studies API is queried
        Then the response status code is "200"
        And study "<study>" is returned

        Examples:
            | user        | study   |
            | datamanager | initial |

    Scenario: Get the total count of all files in a collection
        Given user "<user>" is authenticated
        And the Yoda intake count total files API is queried with collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Get list of all unrecognized and unscanned files
        Given user "<user>" is authenticated
        And the Yoda intake list unrecognized files API is queried with collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Get list of all datasets
        Given user "<user>" is authenticated
        And the Yoda intake list datasets API is queried with collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Scan for and recognize datasets in study intake area
        Given user "<user>" is authenticated
        And the Yoda intake scan for datasets API is queried with collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Lock dataset in study intake area
        Given user "<user>" is authenticated
        And dataset exists
        And the Yoda intake lock API is queried with dataset id and collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Unlock dataset in study intake area
        Given user "<user>" is authenticated
        And dataset exists
        And the Yoda intake unlock API is queried with dataset id and collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Get all details for a dataset
        Given user "<user>" is authenticated
        And dataset exists
        And the Yoda intake dataset get details API is queried with dataset id and collection "<collection>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      |
            | datamanager | /tempZone/yoda/home/grp-initial |
            | researcher  | /tempZone/yoda/home/grp-initial |

    Scenario: Add a comment to a dataset
        Given user "<user>" is authenticated
        And dataset exists
        And the Yoda intake dataset add comment API is queried with dataset id, collection "<collection>" and comment "<comment>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | collection                      | comment |
            | datamanager | /tempZone/yoda/home/grp-initial | initial |
            | researcher  | /tempZone/yoda/home/grp-initial | initial |

    Scenario: Get vault dataset related counts for reporting for a study
        Given user "<user>" is authenticated
        And the Yoda intake report vault dataset counts per study API is queried with study id "<study_id>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id   |
            | datamanager | initial    |

    Scenario: Get aggregated vault dataset info for reporting for a study
        Given user "<user>" is authenticated
        And the Yoda intake report vault aggregated info API is queried with study id "<study_id>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id |
            | datamanager | initial  |

    Scenario: Get vault data required for export for a study
        Given user "<user>" is authenticated
        And the Yoda intake report export study data API is queried with study id "<study_id>"
        Then the response status code is "200"
        # And ...

        Examples:
            | user        | study_id |
            | datamanager | initial  |
