Feature: Datarequest get

  Scenario Outline: Datarequest get
    Given that Yoda is queried with request ID "<request_id>"
    Then the response status code is "200"
    And results are returned for "<request_id>"

    Examples:
    | request_id | 1601287922 |
