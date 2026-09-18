"""This class contains utility functions related to metadata schemas."""

__copyright__ = 'Copyright (c) 2025-2026, Utrecht University'
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


def is_valid_schema_identifier(identifier: str) -> bool:
    """Validate composed schema identifier format.

    - String of max 50 characters
    - Alphanumeric only (A-Za-z0-9)

    :param identifier: Composed schema identifier to validate

    :returns: True if valid, False otherwise
    """
    if not identifier or not isinstance(identifier, str):
        return False
    if len(identifier) > 50:
        return False
    if not identifier.isalnum():
        return False
    return True


def is_valid_blocks_list(available_blocks: list, blocks: list) -> bool:
    """Validate schema building blocks list.

    - Non-empty list
    - Max 10 building blocks
    - No duplicate building blocks
    - All building blocks should be available on the system
    - Each block is a non-empty string

    :param available_blocks: List of available building block identifiers
    :param blocks:           List of block identifiers to validate

    :returns: True if valid, False otherwise
    """
    if not available_blocks or not isinstance(available_blocks, list):
        return False
    if not blocks or not isinstance(blocks, list):
        return False
    if len(blocks) > 10:
        return False
    if len(blocks) != len(set(blocks)):
        return False
    if not all(isinstance(block, str) and block.strip() for block in blocks):
        return False

    try:
        if not all(block in available_blocks for block in blocks):
            return False
    except Exception:
        return False

    return True


def build_composed_schema(schemas: list, blocks: list) -> dict:
    """Build a composed metadata schema from list of building blocks."""
    if not blocks:
        return {}

    if len(blocks) == 1:
        return blocks[0]

    return {}
