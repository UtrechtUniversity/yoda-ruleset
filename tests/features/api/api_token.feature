Feature: Token API

    Scenario: Token generate
        Given user "researcher" is authenticated
        And the Yoda token generate API is queried with "<label>"
        Then the response status code is "200"

        Examples:
            | label            |
            | api_test_token_1 |
            | api_test_token_2 |
            | api_test_token_3 |
            | api_test_token_4 |
            | api_test_token_5 |

    Scenario: Token load
        Given user "researcher" is authenticated
        And the Yoda token load API is queried
        Then the response status code is "200"
        And all tokens are returned

    Scenario: Token delete
        Given user "researcher" is authenticated
        And the Yoda token delete API is queried with "<label>"
        Then the response status code is "200"

        Examples:
            | label            |
            | api_test_token_1 |
            | api_test_token_2 |
            | api_test_token_3 |
            | api_test_token_4 |
            | api_test_token_5 |
