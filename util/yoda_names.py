# -*- coding: utf-8 -*-

"""This class contains utility functions that process names of Yoda entities (e.g. category names, user names, etc.)
"""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

from config import config
from datetime import datetime


def is_valid_category(name):
    """Is this name a valid category name?

    :param name: name of the category

    :returns: boolean value that indicates whether this name is a valid category name
    """
    return re.search(r"^[a-zA-Z0-9\-_]+$", name) is not None


def is_valid_subcategory(name):
    """Is this name a valid subcategory name?

    :param name: name of the subcategory

    :returns: boolean value that indicates whether this name is a valid subcategory name
    """
    return is_valid_category(name)


def is_valid_groupname(name):
    """Is this name a valid group name

    :param name: name of the group

    :returns: boolean value that indicates whether this name is a valid group name
    """
    return re.search(r"^[a-zA-Z0-9\-]+$", name) is not None and len(name) < 64


def is_email_username(name):
    """Is this name a valid email username?

       :param name: name of the user

       :returns: boolean value that indicates whether this name is a valid email username
    """
    return re.search(r'@.*[^\.]+\.[^\.]+$', name) is not None


def is_internal_user(username):
    """Determines if a username refers to an internal user (a user in one of
       the internal domains)

       :param username: name of the user

       :returns: boolean value that indicates whether this username refers to an an internal user
"""
    return _is_internal_user(username, config.external_users_domain_filter)


def _is_internal_user(username, external_domain_filter):
    if '@' not in username:
        return True

    for domain in external_domain_filter:
        if domain.startswith("*."):
            if username.endswith(domain[1:]) or username.endswith("@" + domain[2:]):
                return True
        else:
            if username.endswith("@" + domain):
                return True

    return False


def is_valid_expiration_date(expiration_date):
    """Validation of expiration date.

    :param expiration_date: String containing date that has to be validated

    :returns: Indication whether expiration date is an accepted value
    """
    # Copied from rule_group_expiration_date_validate
    if expiration_date in ["", "."]:
        return True

    try:
        if expiration_date != datetime.strptime(expiration_date, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError

        # Expiration date should be in the future
        if expiration_date <= datetime.now().strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False


def is_valid_schema_id(schema_id):
    """Is this schema at least a correctly formatted schema-id?"""
    if schema_id == "":
        return True
    return re.search(r"^[a-zA-Z0-9\-]+\-[0-9]+$", schema_id) is not None