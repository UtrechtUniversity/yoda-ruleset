Feature: Revisions API

    Scenario: Search revisions on file name 
        Given user "<user>" is authenticated
        And the Yoda revision API is queried with "<filename>"
	    Then the response status code is "200"
	    And "<revision_search_result>" is found 

        Examples:
        | user       | filename      | revision_search_result |
	    | researcher | SIPI          | SIPI_Jelly_Beans       |


    Scenario: Find actual revisions for one perticular dataobject
        Given user "<user>" is authenticated
        Given the Yoda revision API is queried with "<path>"
	    Then the response status code is "200"
	    And revisions list is found 

        Examples:
        | user       | path                                                                  |
        | researcher | /tempZone/home/research-initial/testdata/SIPI_Jelly_Beans_4.1.07.tiff |


    Scenario: Restore a revision 
        Given user "<user>" is authenticated
        And the Yoda revision API is requested to restore "<revision_id>" in collection "<coll_target>" with name "<new_filename>"
	    Then the response status code is "200"
	    And revision is restored successfully

       Examples:
        | user       | revision_id | coll_target                    | new_filename       | 
        | researcher | 10427       | /tempZone/home/research-browse | SIPI_Jelly_Beans_2.tiff | 
