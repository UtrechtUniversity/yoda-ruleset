#! /bin/bash
# This command is for setting up the database for token management

UNENCRYPTED=/etc/irods/yoda-ruleset/tokens.db
DBNAME="$1"

IFS= read -r PASSWORD

if [ -z "$PASSWORD" ]
then echo "Error: refusing to create token database without a password." >&2
     exit 1
fi

if [ -f "$UNENCRYPTED" ]
then
    # convert unencrypted database
    printf "ATTACH DATABASE '%s' AS encrypted KEY '%s'; SELECT sqlcipher_export('encrypted'); DETACH DATABASE encrypted;\n" "$DBNAME" "$PASSWORD" \
	    | sqlcipher "$UNENCRYPTED" && rm "$UNENCRYPTED"
else
    touch "$DBNAME"
    printf "PRAGMA key='%s'; CREATE TABLE IF NOT EXISTS tokens (user TEXT NOT NULL, label TEXT NOT NULL, token TEXT NOT NULL, gen_time INTEGER, exp_time INTEGER, UNIQUE (user, label) ON CONFLICT ABORT);\n" "$PASSWORD" \
	    | sqlcipher "$DBNAME"
fi
