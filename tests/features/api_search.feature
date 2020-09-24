Feature: Search

  Scenario Outline: File Search
    Given the Yoda file search API is queried with "<file>"
    Then the response status code is "200"
    And results are returned for "<file>"

    Examples: Files
      | file                 |
      | yoda-metadata.json   |
