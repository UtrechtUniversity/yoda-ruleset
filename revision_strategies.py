# -*- coding: utf-8 -*-
"""Functions for revision strategies, which control which revisions are kept and which ones are to
   be discarded."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


def get_revision_strategy(strategy_name):
    """Returns a revision strategy object for a particular revision strategy name. This
       object can be used to obtain information about the revision strategy.

       :param strategy_name: Name of the strategy ("A", B", "Simple"). See
                             See https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                             for an explanation.

       :returns: RevisionStrategy object

       :raises ValueError: if no revision strategy for this name could be found
    """

    # Time to second conversion
    HOURS = 3600
    DAYS = 86400
    WEEKS = 604800

    buckets_configuration = {
        "A": [
            [HOURS * 6, 1, 1],
            [HOURS * 12, 1, 0],
            [HOURS * 18, 1, 0],
            [DAYS * 1, 1, 0],
            [DAYS * 2, 1, 0],
            [DAYS * 3, 1, 0],
            [DAYS * 4, 1, 0],
            [DAYS * 5, 1, 0],
            [DAYS * 6, 1, 0],
            [WEEKS * 1, 1, 0],
            [WEEKS * 2, 1, 0],
            [WEEKS * 3, 1, 0],
            [WEEKS * 4, 1, 0],
            [WEEKS * 8, 1, 0],
            [WEEKS * 12, 1, 0],
            [WEEKS * 16, 1, 0]
        ],
        "B": [
            [HOURS * 12, 2, 1],
            [DAYS * 1, 2, 1],
            [DAYS * 3, 2, 0],
            [DAYS * 5, 2, 0],
            [WEEKS * 1, 2, 1],
            [WEEKS * 3, 2, 0],
            [WEEKS * 8, 2, 0],
            [WEEKS * 16, 2, 0]
        ],
        "Simple": [
            [WEEKS * 16, 16, 0],
        ]
    }

    if strategy_name in buckets_configuration:
        return RevisionStrategy(strategy_name, buckets_configuration[strategy_name])
    else:
        raise ValueError('Strategy "{}" is not supported'.format(strategy_name))


class RevisionStrategy(object):
    HOURS = 3600
    DAYS = 86400
    WEEKS = 604800

    def __init__(self, strategy_name, buckets_configuration):
        self._name = strategy_name
        self._buckets = buckets_configuration

    def get_name(self):
        return self._name

    def get_buckets(self):
        return self._buckets

    def get_minimum_bucket_size(self):
        return min(map(lambda bucket_timespan_bucket_size_offset: bucket_timespan_bucket_size_offset[1], self.get_buckets()))

    def get_total_bucket_timespan(self):
        return sum(map(lambda bucket_timespan_bucket_size_offset1: bucket_timespan_bucket_size_offset1[0], self.get_buckets()))
