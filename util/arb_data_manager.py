"""This file contain functions that implement cached data storage for automatic resource
   balancing, which takes care of ensuring that new data objects are put on resources that
   have enough space available.
"""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import TYPE_CHECKING

import genquery

import cached_data_manager
import constants
import log
import msi

if TYPE_CHECKING:
    import rule


class ARBDataManager(cached_data_manager.CachedDataManager):
    AVU_NAME = "yoda::arb"

    def get(self, ctx: 'rule.Context', keyname: str) -> str:
        """Retrieves data from the cache if possible, otherwise retrieves the original.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key

        :returns: Data for this key (arb_status)
        """
        value = super().get(ctx, keyname)
        return constants.arb_status[value]

    def put(self, ctx: 'rule.Context', keyname: str, data: str) -> None:
        """Update both the original value and cached value (if cache is not available, it is not updated)

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key
        :param data:    Data for this key (arb_status)
        """
        super().put(ctx, keyname, data.value)

    def _get_context_string(self) -> str:
        """Returns a string that identifies the particular type of data manager.

        :returns: context string for this type of data manager
        """
        return "arb"

    def _get_original_data(self, ctx: 'rule.Context', keyname: str) -> str:
        """This function is called when data needs to be retrieved from the original (non-cached) location.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key

        :returns: Original data for this key
        """
        arb_data = list(genquery.row_iterator(
            "META_RESC_ATTR_VALUE",
            f"META_RESC_ATTR_NAME = '{self.AVU_NAME}' AND RESC_NAME = '{keyname}'",
            genquery.AS_LIST, ctx))

        if len(arb_data) == 0:
            # If we don't have an ARB value, ARB should ignore this resource
            return constants.arb_status.IGNORE.value
        elif len(arb_data) == 1:
            return arb_data[0][0]
        else:
            log.write(ctx, f"WARNING: multiple ARB AVUs present for resource '{keyname}'. ARB will ignore it.")
            return constants.arb_status.IGNORE.value

    def _put_original_data(self, ctx: 'rule.Context', keyname: str, data: str) -> None:
        """This function is called when data needs to be updated in the original (non-cached) location.

        :param ctx:     Combined type of a callback and rei struct
        :param keyname: Name of the key
        :param data:    Data for this key
        """
        msi.mod_avu_metadata(ctx, "-r", keyname, "set", self.AVU_NAME, data, "")

    def _should_populate_cache_on_get(self) -> bool:
        """This function controls whether the manager populates the cache after retrieving original data.

        :returns: Boolean value that states whether the cache should be populated when original data
                  is retrieved.
        """
        return True
