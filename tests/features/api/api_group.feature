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
        Given user "<user>" is authenticated
        And the user searches for users matching "<pattern>"
        Then the response status code is "200"
        And the result is equal to "<users>"

        Examples:
            | user          | pattern   | users                                         |
            | datamanager   | test      | testuseradd#tempZone, testuserdel#tempZone    |
            | datamanager   | tech      | technicaladmin#tempZone                       |
            | groupmanager  | tech      | technicaladmin#tempZone                       |

    Scenario: Group creation
        Given user "technicaladmin" is authenticated
        And the group "testGroupie" does not exist
        And the user creates a new group "testGroupie"
        Then the response status code is "200"
        And the group "testGroupie" is created

    Scenario: Group update
        Given user "technicaladmin" is authenticated
        And the group "testGroupie" exists
        And the user updates group "testGroupie"
        Then the response status code is "200"
        And the update to group "testGroupie" is persisted

    Scenario: Adding user to group
        Given user "technicaladmin" is authenticated
        And the user X "sterlingarcher" is not a member of group "testGroupie"
        And the user adds user X to the group
        Then the response status code is "200"
        And user X is now a member of the group

    Scenario: Group user update role
        Given user "technicaladmin" is authenticated
        And the user X "sterlingarcher" is a member of group "testGroupie"
        And the user updates the role of user X
        Then the response status code is "200"
        And the update is persisted

    Scenario: Remove user from group
        Given user "technicaladmin" is authenticated
        And the user X "sterlingarcher" is a member of group "testGroupie"
        And the user removes user X from the group
        Then the response status code is "200"
        And user X is no longer a member of the group

    Scenario: Group delete
        Given user "technicaladmin" is authenticated
        And the group "testGroupie" exists
        And the user deletes group "testGroupie"
        Then the response status code is "200"
        And the group "testGroupie" no longer exists
