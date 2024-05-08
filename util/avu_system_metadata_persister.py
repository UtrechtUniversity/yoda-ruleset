# -*- coding: utf-8 -*-
"""A class for storing system metadata in AVUs
"""

__copyright__ = 'Copyright (c) 2016-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import avu
import msi
from constants import ObjectType, UUORGMETADATAPREFIX
from system_metadata_persister import SystemMetadataPersister


class AVUSystemMetadataPersister(SystemMetadataPersister):
    """This class defines functions for storing and retrieving system metadata
       for a particular subsystem of Yoda (e.g. the data health subsystem for
       monitoring data object health).

       The persister allows to store key/value-pairs for each iRODS object in the
       zone. Keys and values are both strings.  A persister is divided into
       namespaces, so that different subsystems of Yoda can both use a
       SystemMetadataPersister, without the risk of name conflicts.
    """

    def __init__(self, namespace):
        if "%" in namespace or "_" in namespace:
            raise Exception("Namespaces cannot contain underscores or percent signs.")
        self.namespace = namespace

    def _get_prefix(self):
        return UUORGMETADATAPREFIX + self.namespace + "_"

    def _get_attr_for_key(self, key_name):
        return self._get_prefix + key_name

    def _get_mod_avu_flag_for_object_type(self, object_type):
        lookup_table = {
            ObjectType.DATAOBJECT: "-d",
            ObjectType.COLLECTION: "-C",
            ObjectType.USER: "-u",
            ObjectType.RESOURCE: "-R"}

        if object_type in lookup_table:
            return lookup_table[object_type]
        else:
            raise Exception("No logic for object type: " + object_type)

    def get(self, ctx, object_type, object_name, key_name):
        """Returns the value for a particular key on a particular object,
           or None if it does not exist.

           :param ctx:         Combined type of a callback and rei struct
           :param object_type: iRODS object type (e.g. collection, resource), as
                               defined in constants.py
           :param object_name: name of the iRODS object
           :param key_name:    name of the key

           :returns:           the value, or None if the key could not be found.

           :raises Exception:  if not implemented, or if an error occurred.
        """
        if (object_type == ObjectType.DATAOBJECT):
            all_avus = avu.of_data(ctx, object_name)
        elif (object_type == ObjectType.COLLECTION):
            all_avus = avu.of_coll(ctx, object_name)
        elif (object_type == ObjectType.USER):
            all_avus = avu.of_user_or_group(ctx, object_name)
        elif (object_type == ObjectType.RESOURCE):
            all_avus = avu.of_resource(ctx, object_name)
        else:
            raise Exception("Unknown object type: " + object_type)

        for this_avu in all_avus:
            if this_avu.attr == self._get_attr_for_key(key_name):
                return this_avu.value

        return None

    def put(self, ctx, object_type, object_name, key_name, value):
        """Sets or updates the value for a particular key on a particular object.

           :param ctx:         Combined type of a callback and rei struct
           :param object_type: iRODS object type (e.g. collection, resource), as
                               defined in constants.py
           :param object_name: name of the iRODS object
           :param key_name:    name of the key. Implementations should support at
                               least 128 byte keys, and at least alphanumeric characters,
                               as well as underscores.
           :param value:       new value. Implementations should support at least
                               1024 byte values.

           :raises Exception:  if not implemented, or if an error occurred.  # noqa DAR402
        """
        object_type_flag = self._get_mod_avu_flag_for_object_type(object_type)
        attribute_name = self.get_attr_for_key(key_name)
        msi.mod_avu_metadata(ctx,
                             object_type_flag,
                             object_name,
                             "set",
                             attribute_name,
                             value,
                             "")

    def rm(self, ctx, object_type, object_name, key_name, ignore_not_found=False):
        """Removes a particular key on a particular iRODS object.

           :param ctx:              Combined type of a callback and rei struct
           :param object_type:      iRODS object type (e.g. collection, resource), as
                                    defined in constants.py
           :param object_name:      name of the iRODS object
           :param key_name:         name of the key
           :param ignore_not_found: do not raise an exception if key was not found
                                    (default: false)

           :raises Exception:  if not implemented, or if an error occurred.
        """
        object_type_flag = self._get_mod_avu_flag_for_object_type(object_type)
        attribute_name = self.get_attr_for_key(key_name)
        current_value = self.get(ctx, object_type, object_name, key_name)
        if current_value is None and not ignore_not_found:
            raise Exception("AVU " + key_name + " for object " + object_name + " was not found.")
        msi.rmw_avu_metadata(ctx,
                             object_type_flag,
                             object_name,
                             "rm",
                             attribute_name,
                             current_value,
                             "")
