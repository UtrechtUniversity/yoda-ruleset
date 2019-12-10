# -*- coding: utf-8 -*-
"""Utilities for performing iRODS genqueries."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from collections import OrderedDict
from enum import Enum

import genquery
import irods_types
# import log

class Option(object):
    """iRODS QueryInp option flags - used internally.

    AUTO_CLOSE, RETURN_TOTAL_ROW_COUNT, and UPPER_CASE_WHERE should not be set
    by calling code, as Query already provides convenient functionality for this.

    See irods: lib/core/include/rodsGenQuery.h
    """
    RETURN_TOTAL_ROW_COUNT = 0x020
    NO_DISTINCT            = 0x040
    QUOTA_QUERY            = 0x080
    AUTO_CLOSE             = 0x100
    UPPER_CASE_WHERE       = 0x200

class OutputType(Enum):
    """
    AS_DICT: result rows are dicts of (column_name => value)
    AS_LIST: result rows are lists of cells (ordered by input column list)

    Note that when using AS_DICT, operations on columns (MAX, COUNT, ORDER, etc.)
    become part of the column name in the result.
    """
    AS_DICT  = 0
    AS_LIST  = 1
    AS_TUPLE = 2

AS_DICT  = OutputType.AS_DICT
AS_LIST  = OutputType.AS_LIST
AS_TUPLE = OutputType.AS_TUPLE

class Query(object):
    """Wrapper for genquery that supports options omitted in the built-in row_iterator.

    :param ctx:            iRODS callback or ctx.
    :param columns:        a list of SELECT column names, or columns as a comma-separated string.
    :param condition:      (optional) where clause, same as row_iterator
    :param output:         (optional) [default=AS_TUPLE] either AS_DICT/AS_LIST/AS_TUPLE, similar to row_iterator
    :param offset:         (optional) starting row (0-based), can be used for pagination
    :param limit:          (optional) maximum amount of results, can be used for pagination
    :param case_sensitive: (optional) set this to False to make the entire where-clause case insensitive
    :param options:        (optional) other OR-ed options to pass to the query (see the Option type above)

    Benefits:

    - Can count total rows without fetching them (needed for queries where
      COUNT() on a single column doesn't suffice)
    - Can pass an offset to skip fetching unneeded rows.
    - Handles case-insensitive queries.
    - Closes the query more efficiently when total row count is high

    Getting the total row count:

      Use q.total_rows() to get the total number of results matching the query
      (without taking offset/limit into account).

      Use len(q) (where q is a Query) to get the amount of results
      *within* the specified offset/limit, if any.

    Output types:

      AS_LIST and AS_DICT behave the same as in row_iterator.
      AS_TUPLE produces a tuple, similar to AS_LIST, with the exception that
      for queries on single columns, each result is returned as a string
      instead of a 1-element tuple.

    Examples:

        # Print all collections.
        for x in Query(callback, 'COLL_NAME'):
            print('name: ' + x)

        # The same, but more verbose:
        for x in Query(callback, 'COLL_NAME', output=AS_DICT):
            print('name: {}'.format(x['COLL_NAME']))

        # ... or make it into a list
        colls = list(Query(callback, 'COLL_NAME'))

        # ... or get data object paths
        datas = ['{}/{}'.format(x, y) for x, y in Query(callback, 'COLL_NAME, DATA_NAME')]

        # Print all data objects, ordered descending by data name, owned by a
        # username containing 'r' or 'R', in a collection under
        # (case-insensitive) '/tempzone/'.
        for x in Query(ctx, 'COLL_NAME, ORDER_DESC(DATA_NAME), DATA_OWNER_NAME',
                       "DATA_OWNER_NAME like '%r%' and COLL_NAME like '/tempzone/%'",
                       case_sensitive=False):
            print('name: {}/{} - owned by {}'.format(*x))
    """

    def __init__(self,
                 ctx,
                 columns,
                 conditions='',
                 output=AS_TUPLE,
                 offset=0,
                 limit=None,
                 case_sensitive=True,
                 options=0):

        self.ctx = ctx

        if type(columns) is str:
            # Convert to list for caller convenience.
            columns = [x.strip() for x in columns.split(',')]

        # Boilerplate.
        self.columns    = columns
        self.conditions = conditions
        self.output     = output
        self.offset     = offset
        self.limit      = limit
        self.options    = options

        if not case_sensitive:
            # Uppercase the entire condition string. Should cause no problems,
            # since query keywords are case insensitive as well.
            self.options   |= Option.UPPER_CASE_WHERE
            self.conditions = self.conditions.upper()

        self.gqi = None  # (genquery inp)
        self.gqo = None  # (genquery out)
        self.cti = None  # (continue index)

        # Filled when calling total_rows() on the Query.
        self._total = None

    def exec_if_not_yet_execed(self):
        if self.gqi is not None:
            return

        self.gqi = self.ctx.msiMakeGenQuery(', '.join(self.columns),
                                            self.conditions,
                                            irods_types.GenQueryInp())['arguments'][2]
        if self.offset > 0:
            self.gqi.rowOffset = self.offset
        else:
            # If offset is 0, we can (relatively) cheaply let iRODS count rows.
            # - with non-zero offset, the query must be executed twice if the
            #   row count is needed (see total_rows()).
            self.options |= Option.RETURN_TOTAL_ROW_COUNT

        if self.limit is not None and self.limit < genquery.MAX_SQL_ROWS - 1:
            # We try to limit the amount of rows we pull in, but ultimately this is not very effective:
            # In order to close the query, 256 more rows will (if available) be fetched regardless.
            self.gqi.maxRows = self.limit

        self.gqi.options |= self.options

        self.gqo    = self.ctx.msiExecGenQuery(self.gqi, irods_types.GenQueryOut())['arguments'][1]
        self.cti    = self.ctx.msiGetContInxFromGenQueryOut(self.gqo, 0)['arguments'][1]
        self._total = None

        # log._write(self.ctx, str(self))

    def total_rows(self):
        """Returns the total amount of rows matching the query.

        This includes rows that are omitted from the result due to limit/offset parameters.
        """
        if self._total is None:
            if self.offset == 0 and self.options & Option.RETURN_TOTAL_ROW_COUNT:
                # Easy mode: Extract row count from gqo.
                self.exec_if_not_yet_execed()
                self._total = self.gqo.totalRowCount
            else:
                # Hard mode: for some reason, using PostgreSQL, you cannot get
                # the total row count when an offset is supplied.
                # When RETURN_TOTAL_ROW_COUNT is set in combination with a
                # non-zero offset, iRODS solves this by executing the query
                # twice[1], one time with no offset to get the row count.
                # Apparently this does not work (we get the correct row count, but no rows).
                # So instead, we run the query twice manually. This should
                # perform only slightly worse.
                # [1]: https://github.com/irods/irods/blob/4.2.6/plugins/database/src/general_query.cpp#L2393
                self._total = Query(self.ctx, self.columns, self.conditions, limit=0,
                                    options=self.options|Option.RETURN_TOTAL_ROW_COUNT).total_rows()

        return self._total

    def __len__(self):
        """Get the amount of results in this query, within provided limit/offset"""
        x = max(0, self.total_rows() - self.offset)
        return x if self.limit is None else min(x, self.limit)

    def __iter__(self):
        self.exec_if_not_yet_execed()

        row_i = 0

        while True:
            try:
                for r in range(self.gqo.rowCnt):
                    if self.limit is not None and row_i >= self.limit:
                        self._close()
                        return

                    row = [self.gqo.sqlResult[c].row(r) for c in range(len(self.columns))]
                    row_i += 1

                    assert self.output in (AS_TUPLE, AS_LIST, AS_DICT)
                    if self.output == AS_TUPLE:
                        yield row[0] if len(self.columns) == 1 else tuple(row)
                    elif self.output == AS_LIST:
                        yield row
                    else:
                        yield OrderedDict(zip(self.columns, row))

            except GeneratorExit:
                self._close()
                return

            if self.cti <= 0 or self.limit is not None and row_i >= self.limit:
                self._close()
                return

            self._fetch()

    def _fetch(self):
        """Fetch the next batch of results"""
        ret      = self.ctx.msiGetMoreRows(self.gqi, self.gqo, 0)
        self.gqo = ret['arguments'][1]
        self.cti = ret['arguments'][2]

    def _close(self):
        """Close the query (prevents filling the statement table)."""
        if not self.cti:
            return

        # msiCloseGenQuery fails with internal errors.
        # Close the query using msiGetMoreRows instead.
        # This is less than ideal, because it may fetch 256 more rows
        # (gqi.maxRows is overwritten) resulting in unnecessary processing
        # work. However there appears to be no other safe way to close the
        # query.

        while self.cti > 0:
            # Close query immediately after getting the next batch.
            # This avoids having to soak up all remaining results, which
            # genquery.row_iterator() currently (4.2.6) appears to do.
            self.gqi.options |= Option.AUTO_CLOSE
            self._fetch()

        # Mark self as closed.
        self.gqi = None
        self.gqo = None
        self.cti = None

    def first(self):
        """Get exactly one result (or None if no results are available)."""
        for x in self:
            self._close()
            return x

    def __str__(self):
        return 'select {}{}{}{}'.format(', '.join(self.columns),
                                        ' where '+self.conditions   if self.conditions else '',
                                        ' limit '+str(self.limit)   if self.limit is not None else '',
                                        ' offset '+str(self.offset) if self.offset else '')

    def __del__(self):
        """Auto-close query on Query destruction"""
        self._close()
