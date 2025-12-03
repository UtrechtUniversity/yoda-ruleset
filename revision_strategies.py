"""Functions for revision strategies, which control which revisions are kept and which ones are to
   be discarded."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List


class RevisionStrategy:
    HOURS = 3600
    DAYS = 86400
    WEEKS = 604800

    def __init__(self, strategy_name: str, buckets_configuration: List, always_keep_one: bool = True) -> None:
        """Create a RevisionStrategy.

        :param strategy_name:         Name of the strategy ("A", B", "Simple", "Fourweeks"). See
                                      https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
                                      for an explanation.
        :param buckets_configuration: List with bucket definitions [timespan, keep_count, offset].
        :param always_keep_one:       If False all revisions that are outside the time window of the buckets will be removed, if True always keep one.
        """
        self._name = strategy_name
        self._buckets = buckets_configuration
        self._always_keep_one = always_keep_one

    def get_name(self) -> str:
        return self._name

    def get_buckets(self) -> List:
        return self._buckets

    def always_keep_one(self) -> bool:
        return self._always_keep_one

    def get_minimum_bucket_size(self) -> int:
        return min((bucket_timespan_bucket_size_offset[1] for bucket_timespan_bucket_size_offset in self.get_buckets()))

    def get_total_bucket_timespan(self) -> int:
        return sum((bucket_timespan_bucket_size_offset1[0] for bucket_timespan_bucket_size_offset1 in self.get_buckets()))


def get_revision_strategy(strategy_name: str) -> RevisionStrategy:
    """Returns a revision strategy object for a particular revision strategy name. This
       object can be used to obtain information about the revision strategy.

       :param strategy_name: Name of the strategy ("A", B", "Simple", "Fourweeks"). See
                             https://github.com/UtrechtUniversity/yoda/blob/development/docs/design/processes/revisions.md
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
            [WEEKS * 16, 16, 0]
        ],
        "Fourweeks": [
            [DAYS * 1, 2, 1],
            [DAYS * 6, 2, 0],
            [DAYS * 21, 2, 0]
        ],
    }

    # Strategies that alays keep one revision.
    always_keep_one_strategies = {"A", "B", "Simple"}

    if strategy_name in buckets_configuration:
        return RevisionStrategy(
            strategy_name,
            buckets_configuration[strategy_name],
            always_keep_one=strategy_name in always_keep_one_strategies,
        )
    raise ValueError(f'Strategy "{strategy_name}" is not supported')
