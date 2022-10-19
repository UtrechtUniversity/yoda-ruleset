Feature: Settings API

    Scenario Outline: Settings Save
        Given user <user> is authenticated
        And the Yoda settings save API is queried with <attribute> and <value>
        Then the response status code is "200"

        Examples:
            | user           | attribute               | value |
            | researcher     | mail_notifications      | OFF   |
            | technicaladmin | mail_notifications      | OFF   |


    Scenario Outline: Settings Load
        Given user <user> is authenticated
        And the Yoda settings load API is queried
        Then the response status code is "200"
        And <attribute> contains <value>

        Examples:
            | user           | attribute               | value |
            | researcher     | mail_notifications      | OFF   |
            | technicaladmin | mail_notifications      | OFF   |
