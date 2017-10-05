#!/bin/bash
set -e
PHYPATH=$1
HOST=$2
USER=$3
DESTINATION=$4
DESTDIR=$(dirname $DESTINATION)
echo "Calling:"
echo "ssh $USER@$HOST mkdir -p $DESTDIR"
timeout 5s ssh $USER@$HOST mkdir -p $DESTDIR
echo "scp -i $HOME/.ssh/$4 $PHYPATH $USER@$HOST:$DESTINATION"
timeout 5s scp $PHYPATH $USER@$HOST:$DESTINATION
echo "ssh $USER@$HOST chmod g+r $DESTINATION"
timeout 5s ssh $USER@$HOST chmod g+r $DESTINATION
