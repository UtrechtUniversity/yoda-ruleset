#!/bin/bash
# \author       Niek Bats
# \date         2019-01-16
# \file         randomCollCopy.sh
# \brief        copies random collections which matches selected wave ($3) experiment ($4) in between datefrom ($5) and datetill ($6) to a folder ($1)
# \             with a maximum $6 collections, if specified.
# \how to use   store the .sh file and .r file to your linux folder and make it the current directory (using cd)
# \             if you want to copy the collections to your linux subfolder, specify iget ($2). The folder ($1) is created in your current linux folder.
# \             if you want to copy the collections to a yoda subfolder, specify icp ($2) instead. The folder ($1) should be preceeded by the yoda
# \             group-folder (e.g. research-collection/30w-pci, the folder 30w-pci is created by the script)
# \             will be created and the collections copied
# \copyright    Copyright (c) 2018, Utrecht University. All rights reserved
# \dependencies requires login on an irods user (e.g. datamanager) with execution right to this script and permission to execute user icommands
# \usage        bash randomCollCopy.sh <folder> <iget | icp> <wave> <experimentType> <dateFrom> <dateTill> <(optional) amount>

#invalid input handling

if [[ $1 = "" || $2 = "" || $3 = "" || $4 = "" || $5 = "" || $6 = "" ]] || [[ ! $7 -gt 0 && ! $7 = "" ]] ; then
#[[ ! $6 -gt 0 ]] check if = a number and more then 0
 echo "the usage of this script is: "
 echo "bash randomCollCopy.sh <folder> <howtoCopy iget-icp> <wave> <experimentType> <dateFrom> <dateTill> <(optional) amount>"
 echo "where folder, wave, experimentType is text. dateFrom and dateTill is text in YYYY-MM-DD.HH:mm:ss format and amount is an number"
 echo "folder is the created subfolder, when using iget. For icp, the folder to be created should be preceeded by the yoda research-name"
 echo "e.g. 'research-copiedcollection/30w-pci' and you should be a user of research-copiedcollection."
 exit 1
fi

#convert input params to named variables for readability also insta docu of what they are
folder="$1" #is text
copyHow="$2" #iget or icp
wave="$3" #is text
experimentType="$4" #is text
dateFrom="$5" #is text in YYYY-MM-DD.HH:mm:ss format
dateTill="$6" #is text in YYYY-MM-DD.HH:mm:ss format
amount=10 #is a positive number default=10
if [[ $7 != "" ]] ; then
 amount="$7"
fi

if [[ $copyHow != "iget" && $copyHow != "icp" ]] ; then
  echo "Your copy method is not correct. It must either be  'iget' or 'icp'"
  echo "Now it is $copyHow"
  exit 1
fi

#run rule put output in an array
read -ra array <<< $(irule -F randomCollCopy.r "'$wave'" "'$experimentType'" "'$dateFrom'" "'$dateTill'")

#if array is empty give notice and exit
if [ ${#array[@]} -eq 0 ]; then
 echo "couldnt find any collections matching your parameters at the moment"
 echo "possible causes there arent any matches, the servers are down or you dont have a connection"
 exit 1
fi

echo "Selecting $amount items from following list: "
for item in ${array[@]}
do
 echo "$item"
done

#make folder
if [[ "$copyHow" == "iget" ]] ; then 
   mkdir "$folder"
   cd "$folder"
fi
if [[ "$copyHow" == "icp" ]] ; then
   imkdir ../"$folder"
   icd ../"$folder"
 fi

echo "selected: "
#make loop to select amount collections from array
for (( i=0; i<$amount; i++ ));
do
 #select a random collection from list

 if [[ ${#array[@]} -ne 0 ]] ; then
  randomNr=$(( RANDOM % ${#array[@]} ))
  #echo which one is copied and copy
  echo "${array[$randomNr]}"
  if [[ "$copyHow" == "iget" ]] ; then 
    iget -r "${array[$randomNr]}"
  fi
  if [[ "$copyHow" == "icp" ]] ; then
    icp -r "${array[$randomNr]}" .
  fi
 
  #remove from list
  unset array[$randomNr]
  array=( "${array[@]}" )
 fi
done
