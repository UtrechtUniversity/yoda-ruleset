Feature: Meta UI

    Examples:
      | folder           |
      | research-initial |

    Scenario: Save metadata
        Given user "researcher" is logged in
        And module "research" is shown
        When user opens metadata form of folder "<folder>"
        And users fills in metadata form
        And users clicks save button
        Then metadata form is saved as yoda-metadata.json


    Scenario: Delete metadata
        Given user "researcher" is logged in
        And module "research" is shown
        When user opens metadata form of folder "<folder>"
        And users clicks delete all metadata button
        Then metadata is deleted from folder
