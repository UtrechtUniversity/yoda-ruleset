Feature: Revisions API

#OK 
#    Scenario: Search revisions on file name 
#        Given the Yoda revision API is queried with "<filename>"
#	Then the response status code is "200"
#	And "<revision_search_result>" is found 

#        Examples:
#        | filename      | revision_search_result |
#	    | yoda-metadata | yoda-metadata.json |


# OK
#    Scenario: Find actual revisions for one perticular dataobject
#        Given the Yoda revision API is queried with "<path>"
#	Then the response status code is "200"
#	And revisions list is found 

#        Examples:
#        | path                                                |
#        | /tempZone/home/research-process3/yoda-metadata.json |


    Scenario: Restore a revision 
        Given the Yoda revision API is requested to restore "<revision_id>" in collection "<coll_target>" with name "<new_filename>"
	Then the response status code is "200"
	And revision is restored successfully

      Examples:
      | revision_id | coll_target                      | new_filename       | 
      | 10801       | /tempZone/home/research-process3 | yoda-metadata.json | 
