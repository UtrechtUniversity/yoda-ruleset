Feature: Revisions UI

    Scenario: Search revisions on file name
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches revision by name with "<name>"
	    Then revision "<revision>" is found

        Examples:
            | name  | revision                                                |
	        | SIPI  | /research-initial/testdata/SIPI_Jelly_Beans_4.1.07.tiff |
            | lorem | /research-initial/testdata/lorem.txt                    |


    Scenario: Restore a revision
        Given user "researcher" is logged in
        And module "research" is shown
        When the user searches revision by name with "<name>"
        And user restores revision "<revision>"
        Then revision is restored

    Examples:
        | name  | revision                                                |
        | SIPI  | /research-initial/testdata/SIPI_Jelly_Beans_4.1.07.tiff |
        | lorem | /research-initial/testdata/lorem.txt                    |


    #   Examples:
    #    | user       | path                                                                  | coll_target                    | new_filename            |
    #    | researcher | /tempZone/home/research-initial/testdata/SIPI_Jelly_Beans_4.1.07.tiff | /tempZone/home/research-browse | SIPI_Jelly_Beans_2.tiff |
