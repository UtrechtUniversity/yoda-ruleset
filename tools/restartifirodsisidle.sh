#!/bin/bash
HOME="/var/lib/irods"
NLINES=`ips |wc -l`
NPROCS=`expr $NLINES - 2`

if [[ $NPROCS -eq 0 ]]; then
	echo "RESTARTING IRODS IS SAFE"
	cd $HOME
	./irodsctl restart	
else
	echo "$NPROCS irods jobs running"
	exit $NPROCS
fi
