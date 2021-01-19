#!/bin/bash
#Author Niek Bats
#$1 wave
#$2 experiment
#$3 pseudocode
#lists all files, when found any grp-intake-folder using specified parameter(s) 

#input check and build query
if [[ "$1" != "" ]] #if no wave dont do anything
then
        query="like '%/grp-intake-%' AND DATA_PATH like '%$1%'"
        if [[ "$2" != "" ]]
        then
                query="$query AND DATA_PATH like '%$2%'"
                if [[ "$3" != "" ]]
                then
                        query="$query AND DATA_PATH like '%$3%'"
                fi
        elif [[ "$3" != "" ]]
        then
        exit 1
        fi

echo $query

#icommand format query is in printf format
output=$(iquest ""%s";%s" "SELECT DATA_PATH, DATA_SIZE WHERE DATA_PATH $query")

#echo $output

printf ""Filepath/name";"filesize"\n" > outputIntake.csv
printf "$output" >> outputIntake.csv

fi
