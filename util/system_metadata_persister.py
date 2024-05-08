# -*- coding: utf-8 -*-
"""An interface and factory for storing and retrieving system metadata
   related to iRODS objects (data objects, collections, users,
   resources).

   The main reasons for keeping for having a separate module for this are:
   1. This makes it easier to change the way metadata for particular
      functionality is stored, if needed.
   2. This makes it easier to test functionality that interacts with system
      metadata by mocking the persister.
"""

__copyright__ = 'Copyright (c) 2016-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from avu_system_metadata_persister import AVUSystemMetadataPersister


class SystemMetadataPersisterFactory:
    """Contains function for creating SystemMetadataPersister functions"""

    def __init__(self, namespace):
        """Create a factory for a particular namespace"""

    def get_system_metadata_persister(self):
        return AVUSystemMetadataPersister(self.namespace)


class SystemMetadataPersister:
    """This class defines functions for storing and retrieving system metadata
       for a particular subsystem of Yoda (e.g. the data health subsystem for
       monitoring data object health).

       The persister allows to store key/value-pairs for each iRODS object in the
       zone. Keys and values are both strings.  A persister is divided into
       namespaces, so that different subsystems of Yoda can both use a
       SystemMetadataPersister, without the risk of name conflicts.
    """

    def get(self, ctx, object_type, object_name, key_name):
        """Returns the value for a particular key on a particular object,
           or None if it does not exist.

           :param ctx:         Combined type of a callback and rei struct
           :param object_type: iRODS object type (e.g. collection, resource), as
                               defined in constants.py
           :param object_name: name of the iRODS object
           :param key_name:    name of the key

           :returns:           the value, or None if the key could not be found.  # noqa DAR202

           :raises Exception:  if not implemented, or if an error occurred.
        """
        raise Exception("Not implemented.")

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

           :raises Exception:  if not implemented, or if an error occurred.
        """
        raise Exception("Not implemented.")

    def rm(self, ctx, object_type, object_name, key_name):
        """Removes a particular key on a particular iRODS object.

           :param ctx:         Combined type of a callback and rei struct
           :param object_type: iRODS object type (e.g. collection, resource), as
                               defined in constants.py
           :param object_name: name of the iRODS object
           :param key_name:    name of the key

           :raises Exception:  if not implemented, or if an error occurred.
        """
        raise Exception("Not implemented.")
