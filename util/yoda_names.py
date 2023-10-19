# -*- coding: utf-8 -*-

"""This class contains utility functions that process names of Yoda entitities (e.g. category names, user names, etc.)
"""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

from config import config


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
    """Is this name a valid group name (prefix such as "research-" can be omitted

    :param name: name of the group

    :returns: boolean value that indicates whether this name is a valid group name
    """
    return re.search(r"^[a-zA-Z0-9\-]+$", name) is not None


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
        parts = domain.split('.')
        if parts[0] == '*':
            # Wildcard - search including subdomains
            domain_pattern = "\@([0-9a-z]*\.){0,2}" + parts[-2] + "\." + parts[-1]
        else:
            # No wildcard - search for exact match
            domain_pattern = "@{}$".format(domain)
        if re.search(domain_pattern, username) is not None:
            return True
    return False
