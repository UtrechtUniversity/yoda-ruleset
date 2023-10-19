# -*- coding: utf-8 -*-
"""This file contain functions that implement cached data storage for automatic resource
   balancing, which takes care of ensuring that new data objects are put on resources that
   have enough space available.
"""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import genquery

import cached_data_manager
import constants
import log
import msi


class ARBDataManager(cached_data_manager.CachedDataManager):
    AVU_NAME = "yoda::arb"

    def get(self, ctx, keyname):
        """Retrieves data from the cache if possible, otherwise retrieves
           the original.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key

           :returns:       data for this key (arb_status)
        """
        value = super(ARBDataManager, self).get(ctx, keyname)
        return constants.arb_status[value]

    def put(self, ctx, keyname, data):
        """Update both the original value and cached value (if cache is not available, it is not updated)

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
           :param data: data for this key (arb_status)
        """
        super(ARBDataManager, self).put(ctx, keyname, data.value)

    def _get_context_string(self):
        """ :returns: a string that identifies the particular type of data manager

           :returns: context string for this type of data manager
        """
        return "arb"

    def _get_original_data(self, ctx, keyname):
        """This function is called when data needs to be retrieved from the original
           (non-cached) location.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key

           :returns:       Original data for this key
        """
        arb_data = list(genquery.row_iterator(
            "META_RESC_ATTR_VALUE",
            "META_RESC_ATTR_NAME = '{}' AND RESC_NAME = '{}'".format(self.AVU_NAME, keyname),
            genquery.AS_LIST, ctx))

        if len(arb_data) == 0:
            # If we don't have an ARB value, ARB should ignore this resource
            return constants.arb_status.IGNORE.value
        elif len(arb_data) == 1:
            return arb_data[0][0]
        else:
            log.write(ctx, "WARNING: multiple ARB AVUs present for resource '{}'. ARB will ignore it.".format(keyname))
            return constants.arb_status.IGNORE.value

    def _put_original_data(self, ctx, keyname, data):
        """This function is called when data needs to be updated in the original
           (non-cached) location.

           :param ctx:     Combined type of a callback and rei struct
           :param keyname: name of the key
           :param data:    Data for this key
        """
        msi.mod_avu_metadata(ctx, "-r", keyname, "set", self.AVU_NAME, data, "")

    def _should_populate_cache_on_get(self):
        """This function controls whether the manager populates the cache
           after retrieving original data.

           :returns: Boolean value that states whether the cache should be populated when original data
                     is retrieved.
        """
        return True
