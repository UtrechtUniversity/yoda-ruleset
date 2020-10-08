Feature: Browse API

    Scenario: Browse folder
        Given the Yoda browse folder API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"

        Examples:
            | collection                                | result                       |
            | /tempZone/home/research-initial           | testdata                     |
            | /tempZone/home/research-initial/testdata  | lorem.txt                    |
            | /tempZone/home/research-initial/testdata  | SIPI_Jelly_Beans_4.1.07.tiff |

    Scenario: Browse collections
        Given the Yoda browse collections API is queried with "<collection>"
        Then the response status code is "200"
        And the browse result contains "<result>"
        And the browse result does not contain "<notresult>"

        Examples:
            | collection                       | result          | notresult          |
            |  /tempZone/home/research-initial | testdata        | yoda-metadata.json |
