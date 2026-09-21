"""This class contains utility functions related to metadata schemas."""

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


def is_unsupported_schema(schema_id: str) -> bool:
    """
    Determine whether schema is known to be no longer supported in current
    version of Yoda (deprecated).

    :param schema_id: Identifier of schema to get

    :returns: Boolean that states whether schema ID is known to be deprecated.
              No schema ID (value None) is also counted as unsupported, since
              schema IDs are compulsory in the present version of Yoda. Unknown
              schemas are considered to be not (known to be) unsupported.
    """
    deprecated_ids = [f"https://yoda.uu.nl/schemas/{shortname}/metadata.json"
                      for shortname in
                      ["core-0", "core-1", "default-0", "default-1", "default-2",
                       "hptlab-0", "teclab-0"
                       ]
                      ]
    return schema_id is None or schema_id in deprecated_ids
