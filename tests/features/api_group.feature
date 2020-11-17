Feature: Group API

    Scenario: Group data
        Given user "<user>" is authenticated
        And the Yoda group data API is queried
        Then the response status code is "200"
        And group "<group>" exists

        Examples:
            | user        | group               |
            | researcher  | research-initial    |
            | researcher  | research-initial1   |
            | datamanager | datamanager-initial |

    Scenario: Group data filtered
        Given user "<user>" is authenticated
        And the Yoda group data filtered API is queried with "<user>" and "<zone>"
        Then the response status code is "200"
        And group "<group>" exists

        Examples:
            | user        | zone     | group               |
            | researcher  | tempZone | research-initial    |
            | researcher  | tempZone | research-initial1   |
            | datamanager | tempZone | datamanager-initial |

    Scenario: Group categories
        Given user "<user>" is authenticated
        And the Yoda group categories API is queried
        Then the response status code is "200"
        And category "<category>" exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |

    Scenario: Group subcategories
        Given user "<user>" is authenticated
        And the Yoda group subcategories API is queried with "<category>"
        Then the response status code is "200"
        And category "<category>" exists

        Examples:
            | user        | category |
            | researcher  | initial  |
            | datamanager | initial  |

    Scenario: Group search users
        Given user "datamanager" is authenticated
        And the user searches for users matching "<pattern>"
        Then the response status code is "200"
        And the result is equal to "<users>"

        Examples:
            | pattern   | users                                         |
            | test      | testuseradd#tempZone, testuserdel#tempZone    |
            | tech      | technicaladmin#tempZone                       |

    Scenario: Group creation
        Given user "datamanager" is authenticated
        And the group "testGroupie" does not exist
        And the user creates a new group "testGroupie"
        Then the response status code is "201"
        And the group "testGroupie" is created

    Scenario: Group update
        Given user "datamanager" is authenticated
        And the group "testGroupie" exists
        And the user updates group "testGroupie"
        Then the response status code is "200"
        And the update to group "testGroupie" is persisted

    Scenario: Group delete
        Given user "datamanager" is authenticated
        And the group "testGroupie" exists
        And the user deletes group "testGroupie"
        Then the response status code is "200"
        And the group "testGroupie" no longer exists

    Scenario: User creation
        Given user "datamanager" is authenticated
        And there exists no user named "sterlingarcher"
        And the user creates the new user
        Then the response status code is "201"
        And the new user is persisted

    Scenario: User update
        Given user "datamanager" is authenticated
        And there exists a user X named "sterlingarcher"
        And the user updates user X
        Then the response status code is "200"
        And the user update is persisted

    Scenario: User delete
        Given user "datamanager" is authenticated
        And there exists a user X named "sterlingarcher"
        And the user deletes user X
        Then the response status code is "200"
        And the user no longer exists