#!/bin/sh
group="$1"
irule -F /etc/irods/irods-ruleset-uu/tools/remove-orphan-vault-if-empty.r '*vaultName="'"$group"'"'
