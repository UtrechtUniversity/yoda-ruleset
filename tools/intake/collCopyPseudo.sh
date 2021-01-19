#!/bin/bash 
# \author       Niek Bats
# \date         2019-01-19
# \file         collCopyPseudo.sh
# \brief        copies all collections which matches pseudocodes as passed in a file ($3) and in between datefrom ($4) and datetill ($5) to a folder ($1)
# \how to use   store the .sh file and .r file to your linux folder and make it the current directory (using cd)
# \             if you want to copy the collections to your linux subfolder, specify iget ($2). The folder ($1) is created in your current linux folder.
# \             if you want to copy the collections to a yoda subfolder, specify icp ($2) instead. The folder ($1) should be preceeded by the yoda
# \             group-folder (e.g. research-copiedcollections/pseudocodelist1, the folder pseudocodelist1 is created by the script)
# \copyright    Copyright (c) 2018, Utrecht University. All rights reserved
# \dependencies requires login on an irods user (e.g. datamanager) with execution right to this script and permission to execute user icommands
# \usage        bash randomCollCopy.sh <folder> <iget | icp> <pseudocode filename> <dateFrom> <dateTill>

#invalid input handling

if [[ $1 = "" || $2 = "" || $3 = "" || $4 = "" || $5 = "" ]] ; then
 echo "the usage of this script is: "
 echo "bash randomCollCopy.sh <folder> <howtoCopy iget-icp> <filename holding comma separated pseudecodes> <dateFrom> <dateTill>"
 echo "where folder, howtoCopy is text. dateFrom and dateTill is text in YYYY-MM-DD.HH:mm:ss format"
 echo "folder is the created subfolder, when using iget. For icp, the folder to be created should be preceeded by the yoda research-name "
 echo "e.g. 'research-copiedcollections/pseudocodelist1' and you must be a user of research-copiedcollection."
 exit 1
fi

#convert input params to named variables for readability also insta docu of what they are
folder="$1" #is text
copyHow="$2" #iget or icp
pseudocodeCsvFile="$3" #is filename of file holding pseudocodes
dateFrom="$4" #is text in YYYY-MM-DD.HH:mm:ss format
dateTill="$5" #is text in YYYY-MM-DD.HH:mm:ss format

if [[ $copyHow != "iget" && $copyHow != "icp" ]] ; then
  echo "Your copy method is not correct. It must either be  'iget' or 'icp'"
  echo "Now it is $copyHow"
  exit 1
fi

#Collect comma separated pseudocodes from file
pseudoCodes=`cat $pseudocodeCsvFile`
echo "pseudocodes: $pseudoCodes"

#run rule put output in an array
read -ra array <<< $(irule -F collCopyPseudo.r "'$pseudoCodes'" "'$dateFrom'" "'$dateTill'")

#if array is empty give notice and exit
if [ ${#array[@]} -eq 0 ]; then
 echo "couldnt find any collections matching your parameters at the moment"
 echo "possible causes there arent any matches, the servers are down or you dont have a connection"
 exit 1
fi

#make folder
if [[ "$copyHow" == "iget" ]] ; then 
   mkdir "$folder"
   cd "$folder"
fi
if [[ "$copyHow" == "icp" ]] ; then
   imkdir ../"$folder"
   icd ../"$folder"
fi


echo "Copy selection: "
for item in ${array[@]}
do
 echo "$item"

 if [[ "$copyHow" == "iget" ]] ; then
   iget -r "$item"
 fi
 if [[ "$copyHow" == "icp" ]] ; then
   icp -r "$item" .
 fi
done

