#! /bin/bash
# This command is for setting up the database for token management
touch $1
sqlite3 $1 'CREATE TABLE IF NOT EXISTS tokens (user TEXT NOT NULL, label TEXT NOT NULL, token TEXT NOT NULL, gen_time INTEGER, exp_time INTEGER, UNIQUE (user, label) ON CONFLICT ABORT)'
