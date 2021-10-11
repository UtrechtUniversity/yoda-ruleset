# -*- coding: utf-8 -*-
"""Functions for token management."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


import secrets
import sqlite3
from datetime import datetime, timedelta
from traceback import print_exc

from util import *

__all__ = ['api_generate_token',
           'api_load_tokens',
           'api_delete_token']

# Location of the database that contain the tokens
TOKEN_DB = '/etc/irods/irods-ruleset-uu/tokens.db'

# Lifetime of a token. TODO: Currently NOT actively being checked
TOKEN_LIFETIME = timedelta(hours=72)

# Length of token
TOKEN_LENGTH = 32


@api.make()
def api_generate_token(ctx, label=None):
    def generate_token():
        return secrets.token_urlsafe(TOKEN_LENGTH)

    user_id = user.name(ctx)
    token = generate_token()
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
        result = api.Error('DatabaseError', 'Error occurred while writing to database')

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
