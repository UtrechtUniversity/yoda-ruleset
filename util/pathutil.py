"""Utility / convenience functions for dealing with paths."""
from __future__ import annotations

# (ideally this module would be named 'path', but name conflicts cause too much pain)

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from collections import namedtuple
from enum import Enum
from typing import List, Tuple


class Space(Enum):
    """Differentiates Yoda path types between research and vault spaces."""

    OTHER       = 0
    RESEARCH    = 1
    VAULT       = 2
    DATAMANAGER = 3
    DATAREQUEST = 4
    INTAKE      = 5
    DEPOSIT     = 6

    def __repr__(self) -> str:
        return 'Space.' + self.name


class ObjectType(Enum):
    COLL = 0
    DATA = 1

    def __repr__(self) -> str:
        return 'ObjectType.' + self.name

    def __str__(self) -> str:
        return '-d' if self is ObjectType.DATA else '-C'


def chop(path: str) -> Tuple[str, str]:
    """Split off the rightmost path component of a path.

    /a/b/c -> (/a/b, c)

    :param path: Path to chop

    :returns: Path with rightmost split off
    """
    # In practice, this is the same as os.path.split on POSIX systems,
    # but it's better to not rely on OS-defined path syntax for iRODS paths.
    if path == '/' or len(path) == 0:
        return '/', ''
    else:
        x = path.split('/')
        return '/'.join(x[:-1]), x[-1]


def dirname(path: str) -> str:
    """Return the dirname of a path."""
    return chop(path)[0]  # chops last component off


def basename(path: str) -> str:
    """Return basename of a path."""
    return chop(path)[1]  # chops everything *but* the last component


def chopext(path: str) -> List[str]:
    """Return the extension of a path."""
    return path.rsplit('.', 1)


def info(path: str) -> Tuple[Space, str, str, str]:
    """Parse a path into a (Space, zone, group, subpath) tuple.

    Synopsis: space, zone, group, subpath = pathutil.info(path)

    This can be used to discern research and vault paths, and provides
    group name and subpath information.

    Examples:

    /                              => Space.OTHER,       '',         '',              ''
    /tempZone                      => Space.OTHER,       'tempZone', '',              ''
    /tempZone/yoda/x               => Space.OTHER,       'tempZone', '',              'yoda/x'
    /tempZone/home                 => Space.OTHER,       'tempZone', '',              'home'
    /tempZone/home/rods            => Space.OTHER,       'tempZone', 'rods',          ''
    /tempZone/home/vault-x         => Space.VAULT,       'tempZone', 'vault-x',       ''
    /tempZone/home/vault-x/y       => Space.VAULT,       'tempZone', 'vault-x',       'y'
    /tempZone/home/datamanager-x/y => Space.DATAMANAGER, 'tempZone', 'datamanager-x', 'y'
    /tempZone/home/research-x/y/z  => Space.RESEARCH,    'tempZone', 'research-x',    'y/z'
    etc.

    :param path: Path to parse

    :returns: Tuple with space, zone, group and subpath
    """
    # Turn empty match groups into empty strings.
    def f(x: str) -> str:
        return '' if x is None else x

    def g(m: re.Match, i: int) -> str:
        return '' if i > len(m.groups()) else f(m.group(i))

    def result(s: Space, m: re.Match) -> Tuple[Space, str, str, str]:
        return (s, g(m, 1), g(m, 2), g(m, 3))

    # Try a pattern and report success if it matches.
    def test(r: str, space: Space) -> Tuple[Space, str, str, str] | None:
        m = re.match(r, path)
        return m and result(space, m)

    return (namedtuple('PathInfo', ['space', 'zone', 'group', 'subpath'])  # type: ignore[call-arg]
            (*test('^/([^/]+)/home/(vault-[^/]+)(?:/(.+))?$',         Space.VAULT)
            or test('^/([^/]+)/home/(research-[^/]+)(?:/(.+))?$',     Space.RESEARCH)
            or test('^/([^/]+)/home/(deposit-[^/]+)(?:/(.+))?$',      Space.DEPOSIT)
            or test('^/([^/]+)/home/(datamanager-[^/]+)(?:/(.+))?$',  Space.DATAMANAGER)
            or test('^/([^/]+)/home/(grp-intake-[^/]+)(?:/(.+))?$',   Space.INTAKE)
            or test('^/([^/]+)/home/(intake-[^/]+)(?:/(.+))?$',       Space.INTAKE)
            or test('^/([^/]+)/home/(datarequests-[^/]+)(?:/(.+))?$', Space.DATAREQUEST)
            or test('^/([^/]+)/home/([^/]+)(?:/(.+))?$',              Space.OTHER)
            or test('^/([^/]+)()(?:/(.+))?$',                         Space.OTHER)
            or (Space.OTHER, '', '', '')))  # (matches '/' and empty paths)


def is_archived_datapackage_path(path: str) -> bool:
    """Tests if a path is the top-level collection of an archived data package

    :param path: Path to check

    :returns: True if path refers to top-level collection of data package. Else False.
    """
    return bool(re.match(r"^/[^/]+/home/vault-[^/]+/[^/]+\[\d+\]$", path))
