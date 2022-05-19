# -*- coding: utf-8 -*-
"""Functions for token management."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import secrets
from datetime import datetime, timedelta
from traceback import print_exc

from util import *

from pysqlcipher3 import dbapi2 as sqlite3

__all__ = ['api_token_generate',
           'api_token_load',
           'api_token_delete']


@api.make()
def api_token_generate(ctx, label=None):
    """Generates a token for user authentication.

    :param ctx:   Combined type of a callback and rei struct
    :param label: Optional label of the token

    :returns: Generated token or API error
    """
    def generate_token():
        return secrets.token_urlsafe(config.token_length)

    user_id = user.name(ctx)
    token = generate_token()

    gen_time = datetime.now()
    token_lifetime = timedelta(hours=config.token_lifetime)
    exp_time = gen_time + token_lifetime
    conn = sqlite3.connect(config.token_database)
    result = None

    try:
        with conn:
            conn.execute("PRAGMA key='%s'" % (config.token_db_password))
            conn.execute('''INSERT INTO tokens VALUES (?, ?, ?, ?, ?)''', (user_id, label, token, gen_time, exp_time))
            result = token
    except sqlite3.IntegrityError:
        result = api.Error('TokenExistsError', 'Token with this label already exists')
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error occurred while writing to database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually
    conn.close()

    return result


@api.make()
def api_token_load(ctx):
    """Loads valid tokens of user.

    :param ctx: Combined type of a callback and rei struct

    :returns: Valid tokens
    """
    user_id = user.name(ctx)
    conn = sqlite3.connect(config.token_database)
    result = []

    try:
        with conn:
            for row in conn.execute('''SELECT label, exp_time FROM tokens WHERE user=:user_id AND exp_time > :now''',
                                    {"user_id": user_id, "now": datetime.now()}):
                result.append({"label": row[0], "exp_time": row[1]})
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error occurred while reading database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually
    conn.close()

    return result


@api.make()
def api_token_delete(ctx, label):
    """Deletes a token of the user.

    :param ctx:   Combined type of a callback and rei struct
    :param label: Label of the token

    :returns: Status of token deletion
    """
    user_id = user.name(ctx)
    conn = sqlite3.connect(config.token_database)
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
