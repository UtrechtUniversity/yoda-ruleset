# -*- coding: utf-8 -*-
"""Temporary genquery compatibility module.

https://github.com/irods/irods_rule_engine_plugin_python/pull/34
https://github.com/irods/irods_rule_engine_plugin_python/issues/35

Improves performance for queries using the row_iterator interface.
"""
import query

AS_LIST = query.AS_LIST
AS_DICT = query.AS_DICT


def row_iterator(columns,
                 conditions,
                 row_return,
                 callback):
    return query.Query(callback, columns, conditions, output=row_return)
