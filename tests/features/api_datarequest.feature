Feature: Datarequest

  Scenario Outline: Datarequest get
    Given the Yoda datarequest API is queried with request "<request_id>"
    Then the response status code is "200"
    And request is returned with id "<request_id>"

    Examples:
    | request_id |
    | 1601295614 |
