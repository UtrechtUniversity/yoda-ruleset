#!/bin/bash
PHYPATH=$1
HOST=$2
USER=$3
PRIVATEKEY=$4
DESTINATION=$5
echo "Calling:"
echo "rsync -e \"ssh -i $HOME/.ssh/$4\" --chmod=ugo=r $PHYPATH $USER@$HOST:$DESTINATION"
rsync -v -e ssh --chmod=ugo=r $PHYPATH $USER@$HOST:$DESTINATION
