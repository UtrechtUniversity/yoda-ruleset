# -*- coding: utf-8 -*-
"""Functions for token management."""

__copyright__ = 'Copyright (c) 2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import secrets
from datetime import datetime, timedelta
from traceback import print_exc

from pysqlcipher3 import dbapi2 as sqlite3

from util import *

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
        length = int(config.token_length)
        token = secrets.token_urlsafe(length)
        return token[:length]

    if not token_database_initialized():
        return api.Error('DatabaseError', 'Internal error: token database unavailable')

    user_id = user.name(ctx)
    token = generate_token()

    gen_time = datetime.now()
    token_lifetime = timedelta(hours=config.token_lifetime)
    exp_time = gen_time + token_lifetime
    conn = sqlite3.connect(config.token_database)
    result = None

    try:
        with conn:
            conn.execute("PRAGMA key='%s'" % (config.token_database_password))
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

    if not token_database_initialized():
        return api.Error('DatabaseError', 'Internal error: token database unavailable')

    user_id = user.name(ctx)
    conn = sqlite3.connect(config.token_database)
    result = []

    try:
        with conn:
            conn.execute("PRAGMA key='%s'" % (config.token_database_password))
            for row in conn.execute('''SELECT label, exp_time FROM tokens WHERE user=:user_id AND exp_time > :now''',
                                    {"user_id": user_id, "now": datetime.now()}):
                exp_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S.%f')
                exp_time = exp_time.strftime('%Y-%m-%d %H:%M:%S')
                result.append({"label": row[0], "exp_time": exp_time})
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
    if not token_database_initialized():
        return api.Error('DatabaseError', 'Internal error: token database unavailable')

    user_id = user.name(ctx)
    conn = sqlite3.connect(config.token_database)
    result = None

    try:
        with conn:
            conn.execute("PRAGMA key='%s'" % (config.token_database_password))
            conn.execute('''DELETE FROM tokens WHERE user = ? AND label = ?''', (user_id, label))
            result = api.Result.ok()
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error during deletion from database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually
    conn.close()

    return result


def get_all_tokens(ctx):
    """Retrieve all valid tokens.
    :param ctx: Combined type of a callback and rei struct

    :returns: Valid tokens
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        return []

    if not token_database_initialized():
        return []

    conn = sqlite3.connect(config.token_database)
    result = []
    try:
        with conn:
            conn.execute("PRAGMA key='%s'" % (config.token_database_password))
            for row in conn.execute('''SELECT user, label, exp_time FROM tokens WHERE exp_time > :now''',
                                    {"user_id": user_id, "now": datetime.now()}):
                result.append({"user": row[0], "label": row[1], "exp_time": row[2]})
    except Exception:
        print_exc()
        result = api.Error('DatabaseError', 'Error occurred while reading database')

    # Connection object used as context manager only commits or rollbacks transactions,
    # so the connection object should be closed manually
    conn.close()

    return result


def token_database_initialized():
    """Checks whether token database has been initialized

    :returns: Boolean value
    """
    return os.path.isfile(config.token_database)
