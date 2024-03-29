@api
Feature: Settings API

    Scenario Outline: Settings Save
        Given user <user> is authenticated
        And the Yoda settings save API is queried with <attribute> and <value>
        Then the response status code is "200"

        Examples:
            | user           | attribute               | value |
            | researcher     | mail_notifications      | OFF   |
            | technicaladmin | mail_notifications      | OFF   |
            | researcher     | group_manager_view      | TREE  |
            | technicaladmin | group_manager_view      | TREE  |
            | researcher     | number_of_items         | 10    |
            | technicaladmin | number_of_items         | 10    |
            | researcher     | color_mode              | AUTO  |
            | technicaladmin | color_mode              | AUTO  |


    Scenario Outline: Settings Load
        Given user <user> is authenticated
        And the Yoda settings load API is queried
        Then the response status code is "200"
        And <attribute> contains <value>

        Examples:
            | user           | attribute               | value |
            | researcher     | mail_notifications      | OFF   |
            | technicaladmin | mail_notifications      | OFF   |
            | researcher     | group_manager_view      | TREE  |
            | technicaladmin | group_manager_view      | TREE  |
            | researcher     | number_of_items         | 10    |
            | technicaladmin | number_of_items         | 10    |
            | researcher     | color_mode              | AUTO  |
            | technicaladmin | color_mode              | AUTO  |
