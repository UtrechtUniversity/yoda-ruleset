"""This class contains utility functions related to metadata schemas."""

__copyright__ = 'Copyright (c) 2025-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import copy


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


def is_valid_schema_description(description: str) -> bool:
    """Validate composed schema description.

    - Non-empty string
    - Max 255 characters

    :param description: Composed schema description to validate

    :returns: True if valid, False otherwise
    """
    if not description or not isinstance(description, str):
        return False
    if not description.strip():
        return False
    if len(description) > 255:
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


def is_valid_composed_schema_structure(schema: dict) -> bool:
    """Validate composed metadata schema structure.

    :param schema: The composed metadata schema to validate

    :returns: True if valid, False otherwise
    """
    required_attributes = {
        'identifier': str,
        'name': str,
        'description': str,
        'blocks': list
    }

    for field, expected_type in required_attributes.items():
        if field not in schema:
            return False

        if not isinstance(schema[field], expected_type):
            return False

    return True


def merge_building_blocks(identifier: str, title: str, description: str, schemas: list[dict]) -> dict:
    """Merge building blocks into a single metadata schema.

    :param identifier:  Identifier of metadata schema
    :param title:       Title of metadata schema
    :param description: Description of metadata schema
    :param schemas:     Building blocks for metadata schema

    :returns: Metadata schema
    """
    def normalize(value, block_name):
        if isinstance(value, dict):
            result = {}

            for key, item in value.items():
                if key == "$id":
                    continue

                if key in ("$ref", "$dynamicRef") and isinstance(item, str):
                    item = item.replace(
                        "#/$defs/", f"#/$defs/{block_name}_"
                    )
                    item = item.replace(
                        "#/definitions/", f"#/$defs/{block_name}_"
                    )

                result[key] = normalize(item, block_name)

            return result

        if isinstance(value, list):
            return [normalize(item, block_name) for item in value]

        return value

    definitions = {}
    properties = {}
    required_fields = []

    for block in schemas:
        name = block["title"]
        schema = copy.deepcopy(block)

        if schema.get("required"):
            required_fields.append(name)

        block_defs = {}
        block_defs.update(schema.pop("$defs", {}) or {})
        block_defs.update(schema.pop("definitions", {}) or {})

        for def_name, def_schema in block_defs.items():
            definitions[f"{name}_{def_name}"] = normalize(
                def_schema, name
            )

        definitions[name] = normalize(schema, name)
        properties[name] = {
            "title": name,
            "$ref": f"#/$defs/{name}",
        }

    return {
        "$id": identifier,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "description": description,
        "type": "object",
        "$defs": definitions,
        "properties": properties,
        "required": required_fields,
    }
