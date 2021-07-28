# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with paths."""

# (ideally this module would be named 'path', but name conflicts cause too much pain)

__copyright__ = 'Copyright (c) 2019-2021, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from enum import Enum

import genquery

import msi


class Space(Enum):
    """Differentiates Yoda path types between research and vault spaces."""

    OTHER       = 0
    RESEARCH    = 1
    VAULT       = 2
    DATAMANAGER = 3
    DATAREQUEST = 4
    INTAKE      = 5
    DEPOSIT     = 6

    def __repr__(self):
        return 'Space.' + self.name


class ObjectType(Enum):
    COLL = 0
    DATA = 1

    def __repr__(self):
        return 'ObjectType.' + self.name

    def __str__(self):
        return '-d' if self is ObjectType.DATA else '-C'


def chop(path):
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


def dirname(path):
    """Return the dirname of a path."""
    return chop(path)[0]  # chops last component off


def basename(path):
    """Return basename of a path."""
    return chop(path)[1]  # chops everything *but* the last component


def chopext(path):
    """Return the extension of a path."""
    return path.rsplit('.', 1)


def info(path):
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
    def f(x):
        return '' if x is None else x

    def g(m, i):
        return '' if i > len(m.groups()) else f(m.group(i))

    def result(s, m):
        return (s, g(m, 1), g(m, 2), g(m, 3))

    # Try a pattern and report success if it matches.
    def test(r, space):
        m = re.match(r, path)
        return m and result(space, m)

    from collections import namedtuple

    return (namedtuple('PathInfo', 'space zone group subpath'.split())
            (*test('^/([^/]+)/home/(vault-[^/]+)(?:/(.+))?$',         Space.VAULT)
            or test('^/([^/]+)/home/(research-[^/]+)(?:/(.+))?$',     Space.RESEARCH)
            or test('^/([^/]+)/home/(deposit-[^/]+)(?:/(.+))?$',      Space.DEPOSIT)
            or test('^/([^/]+)/home/(datamanager-[^/]+)(?:/(.+))?$',  Space.DATAMANAGER)
            or test('^/([^/]+)/home/(grp-intake-[^/]+)(?:/(.+))?$',   Space.INTAKE)
            or test('^/([^/]+)/home/(datarequests-[^/]+)(?:/(.+))?$', Space.DATAREQUEST)
            or test('^/([^/]+)/home/([^/]+)(?:/(.+))?$',              Space.OTHER)
            or test('^/([^/]+)()(?:/(.+))?$',                         Space.OTHER)
            or (Space.OTHER, '', '', '')))  # (matches '/' and empty paths)


def object_type(ctx, path):
    try:
        t = msi.get_obj_type(ctx, path, '')['arguments'][1]
    except Exception as e:
        return
    if t == '-d':
        return ObjectType.DATA
    if t == '-c':
        return ObjectType.COLL


def fs_object_from_id(ctx, obj_id):
    """Return (path, ObjectType) for the given object id, or (None, None) if the ID does not exist."""
    x = genquery.Query(ctx, 'COLL_NAME, DATA_NAME', "DATA_ID = '{}'".format(obj_id), genquery.AS_DICT).first() \
        or genquery.Query(ctx, 'COLL_NAME',            "COLL_ID = '{}'".format(obj_id), genquery.AS_DICT).first()

    if x is None:  # obj does not exist.
        return None, None
    elif 'DATA_NAME' in x:
        return '{}/{}'.format(*x.values()), ObjectType.DATA
    else:
        return x['COLL_NAME'], ObjectType.COLL
