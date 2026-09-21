@api
Feature: API (de)serialization using api_ping

# These tests use the api_ping endpoint (only available in development environments)
# to test how strings with different encodings are passed to and/from API endpoints.
# This is meant to test behaviour of the common API code in util/api.py (in combination
# with iRODS and PRC).

    Scenario Outline: The object echo endpoint returns <case> unchanged
        Given user technicaladmin is authenticated
        When the ping API is queried with the "<case>" payload
        Then the response status code is "200"
        And the ping response returns the "<case>" payload unchanged

        Examples:
            | case                   |
            | empty_string           |
            | ascii_only_letters     |
            | ascii_with_numbers     |
            | ascii_with_punctuation |
            | ascii_with_newline     |
            | ascii_long_10k         |
            | non_ascii_letters      |
            | control_chars          |
            | cjk                    |
            | emoji_astral           |
