# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with paths."""

# (ideally this module would be named 'path', but name conflicts cause too much pain)

__copyright__ = 'Copyright (c) 2019, Utrecht University'

import re
from enum import Enum

class Space(Enum):
    """Differentiates Yoda path types between research and vault spaces."""
    OTHER    = 0
    RESEARCH = 1
    VAULT    = 2

    def __repr__(self):
        return 'Space.' + self.name


def chop(path):
    """Split off the rightmost path component of a path.

    /a/b/c -> (/a/b, c)
    """
    # In practice, this is the same as os.path.split on POSIX systems,
    # but it's better to not rely on OS-defined path syntax for iRODS paths.
    if path == '/' or len(path) == 0:
        return '/', ''
    else:
        x = path.split('/')
        return '/'.join(x[:-1]), x[-1]


def info(path):
    """
    Parse a path into a (Space, zone, group, subpath) tuple.

    Synopsis: space, zone, group, subpath = pathutil.info(path)

    This can be used to discern research and vault paths, and provides
    group name and subpath information.

    Examples:

    /                           => Space.OTHER,    '',         '',           ''
    /tempZone                   => Space.OTHER,    'tempZone', '',           ''
    /tempZone/yoda/x            => Space.OTHER,    'tempZone', '',           'yoda/x'
    /tempZone/home              => Space.OTHER,    'tempZone', '',           'home'
    /tempZone/home/vault-x      => Space.VAULT,    'tempZone', 'vault-x',    ''
    /tempZone/home/vault-x/y    => Space.VAULT,    'tempZone', 'vault-x',    'y'
    /tempZone/home/research-x/y => Space.RESEARCH, 'tempZone', 'research-x', 'y'
    etc.
    """

    # Turn empty match groups into empty strings.
    f      = lambda x:    '' if x is None else x
    g      = lambda m, i: '' if i > len(m.groups()) else f(m.group(i))
    result = lambda s, m: (s, g(m, 1), g(m, 2), g(m, 3))

    # Try a pattern and report success if it matches.
    def test(r, space):
        m = re.match(r, path)
        return m and result(space, m)

    return (test('^/([^/]+)/home/(vault-[^/]+)(?:/(.+))?$',    Space.VAULT)
         or test('^/([^/]+)/home/(research-[^/]+)(?:/(.+))?$', Space.RESEARCH)
         or test('^/([^/]+)/home/([^/]+)(?:/(.+))?$',          Space.OTHER)
         or test('^/([^/]+)()(?:/(.+))?$',                     Space.OTHER)
         or (Space.OTHER, '', '', ''))  # (matches '/' and empty paths)


