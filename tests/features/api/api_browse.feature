Feature: Browse API

    Scenario Outline: Browse folder
        Given user <user> is authenticated
        And the Yoda browse folder API is queried with <collection>
        Then the response status code is "200"
        And the browse result contains <result>

        Examples:
            | user        | collection                               | result                       |
            | researcher  | /tempZone/home/research-initial          | testdata                     |
            | researcher  | /tempZone/home/research-initial/testdata | lorem.txt                    |
            | researcher  | /tempZone/home/research-initial/testdata | SIPI_Jelly_Beans_4.1.07.tiff |
            | datamanager | /tempZone/home/research-initial          | testdata                     |
            | datamanager | /tempZone/home/research-initial/testdata | lorem.txt                    |
            | datamanager | /tempZone/home/research-initial/testdata | SIPI_Jelly_Beans_4.1.07.tiff |


    Scenario Outline: Browse collections
        Given user <user> is authenticated
        And the Yoda browse collections API is queried with <collection>
        Then the response status code is "200"
        And the browse result contains <result>
        And the browse result does not contain <notresult>

        Examples:
            | user        | collection                      | result   | notresult          |
            | researcher  | /tempZone/home/research-initial | testdata | yoda-metadata.json |
            | datamanager | /tempZone/home/research-initial | testdata | yoda-metadata.json |


    Scenario Outline: Browse folder with ordering
        Given user <user> is authenticated
        And the Yoda browse folder API is queried on <collection> with sorting on <sort_on> and <sort_order> direction
        Then the response status code is "200"
        And the first row in result contains <result>

        Examples:
            | user        | collection                               | sort_on  | sort_order     | result                       |
            | researcher  | /tempZone/home/research-initial/testdata | name     | asc            | lorem.txt                    |
            | researcher  | /tempZone/home/research-initial/testdata | name     | desc           | SIPI_Jelly_Beans_4.1.07.tiff |
            | researcher  | /tempZone/home/research-initial/testdata | size     | asc            | SIPI_Jelly_Beans_4.1.07.tiff |
            | researcher  | /tempZone/home/research-initial/testdata | size     | desc           | lorem.txt                    |
