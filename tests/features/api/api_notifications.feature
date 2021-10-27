Feature: Notifications API

    Scenario Outline: Notifications load
        Given user "researcher" is authenticated
        And the Yoda notifications load API is queried with sort order "<sort_order>"
        Then the response status code is "200"

        Examples:
            | sort_order |
            | desc       |
            | asc        |

    Scenario Outline: Notifications dismiss all
        Given user "researcher" is authenticated
        And the Yoda notifications dismiss all API is queried
        Then the response status code is "200"
