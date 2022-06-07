#! /bin/bash
# This command is for setting up the database for token management

UNENCRYPTED=/etc/irods/yoda-ruleset/tokens.db
if [ -f $UNENCRYPTED ]
then
    # convert unencrypted database
    sqlcipher $UNENCRYPTED "ATTACH DATABASE '$1' AS encrypted KEY '$2'; SELECT sqlcipher_export('encrypted'); DETACH DATABASE encrypted" && rm $UNENCRYPTED
else
    touch $1
    sqlcipher $1 "PRAGMA key='$2'; CREATE TABLE IF NOT EXISTS tokens (user TEXT NOT NULL, label TEXT NOT NULL, token TEXT NOT NULL, gen_time INTEGER, exp_time INTEGER, UNIQUE (user, label) ON CONFLICT ABORT)"
fi
