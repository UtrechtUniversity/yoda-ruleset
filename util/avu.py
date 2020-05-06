# -*- coding: utf-8 -*-
"""Utility / convenience functions for dealing with AVUs."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery
import itertools
import irods_types

import msi
import query
import pathutil
from query import Query
from collections import namedtuple

Avu = namedtuple('Avu', list('avu'))
Avu.attr  = Avu.a
Avu.value = Avu.v
Avu.unit  = Avu.u


def of_coll(ctx, coll):
    """Get (a,v,u) triplets for a given collection"""
    return itertools.imap(lambda x: Avu(*x),
                          Query(ctx, "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS",
                                     "COLL_NAME = '{}'".format(coll)))


def of_data(ctx, path):
    """Get (a,v,u) triplets for a given data object"""
    return itertools.imap(lambda x: Avu(*x),
                          Query(ctx, "META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE, META_DATA_ATTR_UNITS",
                                     "COLL_NAME = '{}', DATA_NAME = '{}'".format(*pathutil.chop(path))))


def set_on_coll(ctx, coll, a, v):
    """Set key/value metadata on a collection"""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.set_key_value_pairs_to_obj(ctx, x['arguments'][1], coll, '-C')


def rm_from_coll(ctx, coll, a, v):
    """Remove key/value metadata from a collection"""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.remove_key_value_pairs_from_obj(ctx, x['arguments'][1], coll, '-C')


def rm_from_data(ctx, coll, a, v):
    """Remove key/value metadata from a data object"""
    x = msi.string_2_key_val_pair(ctx, '{}={}'.format(a, v), irods_types.BytesBuf())
    msi.remove_key_value_pairs_from_obj(ctx, x['arguments'][1], coll, '-d')


def rmw_from_coll(ctx, obj, a, v, u=''):
    msi.rmw_avu(ctx, '-C', obj, a, v, u)


def rmw_from_data(ctx, obj, a, v, u=''):
    msi.rmw_avu(ctx, '-d', obj, a, v, u)
