#!/bin/sh
group="$2"
irule -F /etc/irods/yoda-ruleset/tools/remove-orphan-vault-if-empty.r '*vaultName="'"$group"'"'
