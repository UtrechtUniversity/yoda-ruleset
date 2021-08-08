# -*- coding: utf-8 -*-
"""Functions for token management"""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *
from util.query import Query
import sqlite3
import sys
from traceback import print_exc
import random
from datetime import datetime, timedelta

__all__ = ['api_generate_token',
           'api_load_tokens',
           'api_delete_token']

# Location of the database that contain the tokens
TOKEN_DB = '/etc/irods/irods-ruleset-uu/tokens.db'
# Lifetime of a token. TODO: Currently NOT actively being checked
TOKEN_LIFETIME = timedelta(minutes=30)


@api.make()
def api_generate_token(ctx, label=None):
    def generate_token(user, label):
        # Ideally all forms of passwords/tokens have a prefix so the
        # correct authentication method can be selected in the PAM stack.
        # Unfortunately there is no way to control all sources of
        # authentication (i.e. iCommands client) so we can't rely on the
        # prefix to tell us what auth method should be used (because in 
        # the iCommands client example the prefixes could be added manually).
        # In the PAM stack itself there is no known way of differentiating between 
        # sources for the authentication request: authentication goes through
        # PamAuthReq_In types of messages which do not contain any information
        # about the source, afaik.
        # TODO: actual randomly generated tokens. Simple here for debugging
        # purposes.
        return user + ':' + label + ':' + str(random.randrange(0,99))

    user_id = user.name(ctx)
    token = generate_token(user_id, label)
    # !!! TODO
    # The timestamps are just for show now; no checking for validity is done
    # and it should be noted that no thought has been put into the strange
    # behaviour of datetimes and timezones/daytime savings
    gen_time = datetime.now()
    exp_time = gen_time + TOKEN_LIFETIME
    conn = sqlite3.connect(TOKEN_DB)
    result = None

    try:
        with conn:
            # TODO: encrypt database so tokens cannot (easily) be read
            conn.execute('''INSERT INTO tokens VALUES (?, ?, ?, ?, ?)''', (user_id, label, token, gen_time, exp_time))
            result = token
    except Exception:
        print_exc()
        result = api.Error('DatabaseError','Error occurred while writing to database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually 
    conn.close()

    return result


@api.make()
def api_load_tokens(ctx):
    user_id = user.name(ctx)
    conn = sqlite3.connect(TOKEN_DB)
    result = []

    try:
        with conn: 
            for row in conn.execute('''SELECT * FROM tokens WHERE user=:user_id''', {"user_id": user_id}):
                result.append({"label": row[1], "gen_time": row[3], "exp_time": row[4]})
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error occurred while reading database') 

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually 
    conn.close()

    return result


@api.make()
def api_delete_token(ctx, label):
    user_id = user.name(ctx)
    conn = sqlite3.connect(TOKEN_DB)
    result = None

    try:
        with conn:
            conn.execute('''DELETE FROM tokens WHERE user = ? AND label = ?''', (user_id, label))
            result = api.Result.ok()
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error during deletion from database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually 
    conn.close()

    return result
