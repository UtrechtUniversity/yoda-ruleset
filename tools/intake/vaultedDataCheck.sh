#!/bin/bash
#Author Niek Bats
#$1 wave
#$2 experiment
#$3 pseudocode
#lists all files, when found any grp-vault-folder using specified parameter(s) 

#input check
if("$1" == "")  do #if no wave kill script
        exit 1
done

#build iquest query
query="%"
for arg in "$@" #add per argument: "$argument/"
do
        if [ "$arg" != "" ]
        then
                query="$query$arg/"
        fi
done

query="$query%"

#icommand format query is in printf format
output=$(iquest ""%s";%s" "SELECT DATA_PATH, DATA_SIZE WHERE DATA_PATH like '$query'")

printf ""Filepath/name";"filesize"\n" > outputVault.csv
printf "$output" >> outputVault.csv
