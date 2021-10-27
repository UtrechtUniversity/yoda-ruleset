Feature: Settings API

    Examples:
        | attribute               | value |
        | mail_notifications      | OFF   |

    Scenario: Settings Save
        Given user "researcher" is authenticated
        And the Yoda settings save API is queried with "<attribute>" and "<value>"
        Then the response status code is "200"

    Scenario: Settings Load
        Given user "researcher" is authenticated
        And the Yoda settings load API is queried
        Then the response status code is "200"
        And "<attribute>" contains "<value>"
