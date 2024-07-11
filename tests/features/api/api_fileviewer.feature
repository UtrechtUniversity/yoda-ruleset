@api
Feature: Fileviewer API

    Scenario Outline: Text file view
        Given user researcher is authenticated
        And the Yoda text file view API is queried with <file>
        Then the response status code is "200"

        Examples:
            | file                                                    |
            | /tempZone/home/research-initial/testdata/lorem.txt      |
            | /tempZone/home/research-initial/testdata/creatures.json |
  

    Scenario Outline: Text file view errors
        Given user researcher is authenticated
        And the Yoda text file view API is queried with <file>
        Then the response status code is "400"
        # 1: non existing file
        # 2: non existing file with .txt extension
        # 3: Too large text file
        # 4: File isn't actually a text file

        Examples:
            | file                                                               |
            | /tempZone/home/research-initial/testdata/nonexisting-file-1234     |
            | /tempZone/home/research-initial/testdata/nonexisting-file-1234.txt |
            | /tempZone/home/research-initial/testdata/large-file.html           |
            | /tempZone/home/research-initial/testdata/image.txt                 |
