Feature: Deposit UI

  Scenario: Deposit page home
    Given user "researcher" is logged in
    And page "deposit" is shown
    Then text "Deposit your data" is shown

  Scenario: Deposit meta page
    Given user "researcher" is logged in
    And page "deposit/metadata/" is shown
    Then text "Deposit Metadata form" is shown

  Scenario: Deposit submit page
    Given user "researcher" is logged in
    And page "deposit/submit/" is shown
    Then text "Submit Deposit" is shown


#  Scenario Outline: Deposit upload
#    Given user "researcher" is authenticated
#    And a file "<file>" is uploaded in "<folder>"
#    Then the response status code is "200"
#    And file "<file>" exists in "<collection>"
#
#  Examples:
#    | file                 | folder            | collection                      |
#    | upload_test_file.txt | /research-initial | /tempZone/home/research-initial |


