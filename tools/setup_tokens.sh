#! /bin/bash
# This command is for setting up the database for token management

touch /etc/irods/irods-ruleset-uu/tokens.db
sqlite3 /etc/irods/irods-ruleset-uu/tokens.db 'create table tokens (user, label, token, gen_time, exp_time)' 
