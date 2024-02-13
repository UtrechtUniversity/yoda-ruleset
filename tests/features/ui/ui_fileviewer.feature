@ui
Feature: Fileviewer UI

    Scenario Outline: Text file view
        Given user researcher is logged in
        When user opens link to fileviewer with "<file>"
        Then the lorem ipsum file is shown

        Examples:
            | file                                 |
            | /research-initial/testdata/lorem.txt |


    Scenario Outline: Text file view errors
        Given user <user> is logged in
        When user opens link to fileviewer with "<file>"
        Then the error message "<message>" is shown

        Examples:
            | user           | file                                              | message               |
            | technicaladmin | /research-initial/testdata/lorem.txt              | not retrieve          |
            | researcher     | /research-initial/testdata/file-with-no-extension | no viewable extension |
            | researcher     | /research-initial/testdata/image.txt              | not a text file       |