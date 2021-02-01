#!/bin/bash
#Author Niek Bats
#$1 wave
#$2 experiment
#$3 pseudocode
#lists all files, when found any grp-vault-folder using specified parameter(s) 

output=$(irule -F youthVaultCheck.r "'$1'" "'$2'" "'$3'")
#echo $output
if [[ "$output" == "" ]]
then
    echo "no results with parameters $1 $2 $3"

elif [[ $output == "Invalid input" ]]
then
    echo "$output"

else
    outputFile="vault-$1"
    if [[ "$2" != "" ]]
    then
        outputFile="$outputFile-$2"
    fi
    if [[ "$3" != "" ]]
    then
        outputFile="$outputFile-$3"
    fi
    outputFile="$outputFile.csv"
    
    printf "\"Filepath\";\"name\";\"extension\";\"filesize\"\n" > "$outputFile"
    printf "$output" >> "$outputFile"
fi
