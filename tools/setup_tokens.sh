#! /bin/bash
# This command is for setting up the database for token management

touch $1
sqlite3 $1 'create table tokens (user, label, token, gen_time, exp_time)'
