"""Functions for handling metadata schemas."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2018-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import re
from collections import defaultdict
from typing import Tuple

import genquery

import admin
import meta
from util import *

__all__ = ['api_schema_get_building_blocks',
           'api_schema_get_composed_schemas',
           'api_schema_get_composed_schema',
           'api_schema_preview_composed_schema',
           'api_schema_post_composed_schema',
           'api_schema_put_composed_schema',
           'api_schema_delete_composed_schema',
           'api_schema_get_schemas']

REQUIRED_BUILDING_BLOCKS = ["descriptive_1-0-0",
                            "citation_1-0-0",
                            "access-rights_1-0-0",
                            "preservation_1-0-0"]


def get_building_blocks(ctx: rule.Context) -> list[dict]:
    """Get schema building blocks from iRODS.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of schema building blocks
    """
    blocks = []
    zone = user.zone(ctx)
    iter = genquery.row_iterator(
        "COLL_NAME",
        f"COLL_PARENT_NAME = '/{zone}/yoda/metadata_schemas' AND META_COLL_ATTR_NAME = '{constants.SCHEMA_USER_SELECTABLE}' AND META_COLL_ATTR_VALUE = 'True'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        block_name = row[0].split('/')[-1]

        metadata_schema = jsonutil.read(ctx, f"/{zone}/yoda/metadata_schemas/{block_name}/metadata.json")
        ui_schema = jsonutil.read(ctx, f"/{zone}/yoda/metadata_schemas/{block_name}/uischema.json")

        blocks.append({
            block_name: {
                "schema": metadata_schema,
                "ui_schema": ui_schema,
                "required": block_name in REQUIRED_BUILDING_BLOCKS,
            }
        })

    return blocks


def get_composed_schemas(ctx: rule.Context) -> list[dict]:
    """Get list of composed schemas from iRODS metadata.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of all composed schemas
    """
    zone = user.zone(ctx)
    avus = avu.of_coll(ctx, f"/{zone}/yoda/composed_schemas")
    composed_schemas = []
    schemas_in_use = get_schema_ids_in_use(ctx)

    for schema in avus:
        if schema.attr.startswith(f"{constants.SCHEMA}_"):
            try:
                composed_schema = jsonutil.fast_parse(schema.value)
            except json.JSONDecodeError as e:
                log.write(ctx, f"Failed to parse schema JSON of <{schema.attr}>: {e}")

            if schema_utils.is_valid_composed_schema_structure(composed_schema):
                composed_schema["in_use"] = composed_schema["identifier"] in schemas_in_use
                composed_schemas.append(composed_schema)
            else:
                log.write(ctx, f"Invalid structure of composed metadata schema <{schema.attr}>: {str(composed_schema)}")

    return composed_schemas


def get_schema_ids_in_use(ctx: rule.Context) -> set[str]:
    """Get schema identifiers assigned to groups."""
    schemas_in_use = set()

    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        "USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'schema_id'",
        genquery.AS_LIST, ctx
    )

    for schema_id, in iter:
        schemas_in_use.add(schema_id)

    return schemas_in_use


@api.make()
def api_schema_get_building_blocks(ctx: rule.Context) -> api.Result:
    """Get list of schema building blocks.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of schema building blocks
    """
    try:
        return get_building_blocks(ctx)
    except Exception:
        return api.Error('internal', 'Could not retrieve list of schema building blocks')


@api.make()
def api_schema_get_composed_schemas(ctx: rule.Context) -> api.Result:
    """Get list of all composed schemas.

    :param ctx: Combined type of a callback and rei struct

    :returns: List of all composed schemas
    """
    return get_composed_schemas(ctx)


@api.make()
def api_schema_get_composed_schema(ctx: rule.Context, identifier: str) -> api.Result:
    """A GET using ID for Compose page to show a composed schema.

    :param ctx:        Combined type of a callback and rei struct
    :param identifier: Composed metadata schema identifier

    :returns: Composed metadata schema
    """
    if not schema_utils.is_valid_schema_identifier(identifier):
        return api.Error('bad_request', 'Invalid composed schema identifier')

    for composed_schema in get_composed_schemas(ctx):
        if composed_schema["identifier"] == identifier:
            schema, uischema = build_composed_schema(ctx, identifier)
            composed_schema["schema"] = schema
            composed_schema["uischema"] = uischema
            return composed_schema

    return api.Error('not_found', 'Could not find composed schema with provided identifier')


@api.make()
def api_schema_preview_composed_schema(ctx: rule.Context, blocks: list) -> api.Result:
    """Preview composed metadata schema from building blocks.

    :param ctx:    Combined type of a callback and rei struct
    :param blocks: List of schema building blocks

    :returns: Composed metadata schema
    """
    building_blocks = get_building_blocks(ctx)
    if not schema_utils.is_valid_blocks_list([list(block.keys())[0] for block in building_blocks], blocks):
        return api.Error('bad_request', 'Invalid schema building block list')

    available_by_id = {
        block_id: block_data
        for item in building_blocks
        for block_id, block_data in item.items()
    }

    schemas = [
        available_by_id[block_ref]["schema"]
        for block_ref in blocks
        if block_ref in available_by_id
    ]

    uischemas = [
        available_by_id[block_ref]["ui_schema"]
        for block_ref in blocks
        if block_ref in available_by_id
    ]

    return schema_utils.merge_building_blocks(
        identifier="metadata-schema-preview-0",
        title="Metadata schema preview",
        description="Metadata schema preview",
        schemas=schemas,
        uischemas=uischemas
    )


@api.make()
def api_schema_post_composed_schema(ctx: rule.Context, identifier: str, name: str, description: str, blocks: list) -> api.Result:
    """A POST for Compose page to save a composed schema.

    :param ctx:         Combined type of a callback and rei struct
    :param identifier:  Composed metadata schema identifier
    :param name:        Name of composed metadata schema
    :param description: Description of composed metadata schema
    :param blocks:      List of schema building blocks

    :returns: Boolean indicating if post succeeded
    """
    if not admin.is_admin(ctx, user.name(ctx)):
        return api.Error('not_allowed', 'Only admins can post composed schemas')
    if not schema_utils.is_valid_schema_identifier(identifier):
        return api.Error('bad_request', 'Invalid composed schema identifier')
    if not schema_utils.is_valid_schema_name(name):
        return api.Error('bad_request', 'Invalid composed schema name')
    if not schema_utils.is_valid_schema_description(description):
        return api.Error('bad_request', 'Invalid composed schema description')
    building_blocks = get_building_blocks(ctx)
    if not schema_utils.is_valid_blocks_list([list(block.keys())[0] for block in building_blocks], blocks):
        return api.Error('bad_request', 'Invalid schema building block list')

    required_blocks = set(REQUIRED_BUILDING_BLOCKS)
    if not required_blocks.issubset(set(blocks)):
        return api.Error('bad_request', 'All required building blocks must be selected')

    for schema in get_composed_schemas(ctx):
        if schema["identifier"] == identifier:
            return api.Error('schema_exists', f"Composed schemas with name <{identifier}> already exists")

    try:
        composed_schema = {
            "identifier": identifier,
            "name": name,
            "description": description,
            "blocks": blocks
        }
        zone = user.zone(ctx)
        avu.set_on_coll(ctx, f"/{zone}/yoda/composed_schemas", f"{constants.SCHEMA}_{identifier}", jsonutil.fast_dump(composed_schema))
    except Exception:
        return api.Error('internal', f"Failed to post composed schemas <{identifier}>")

    return api.Result.ok()


@api.make()
def api_schema_put_composed_schema(ctx: rule.Context, identifier: str, name: str, description: str, blocks: list) -> api.Result:
    """A PUT for Edit page to update a composed schema.

    :param ctx:         Combined type of a callback and rei struct
    :param identifier:  Composed metadata schema identifier
    :param name:        Name of composed metadata schema
    :param description: Description of composed metadata schema
    :param blocks:      List of schema building blocks

    :returns: Boolean indicating if put succeeded
    """
    if not admin.is_admin(ctx, user.name(ctx)):
        return api.Error('not_allowed', 'Only admins can put composed schemas')
    if not schema_utils.is_valid_schema_identifier(identifier):
        return api.Error('bad_request', 'Invalid composed schema identifier')
    if not schema_utils.is_valid_schema_name(name):
        return api.Error('bad_request', 'Invalid composed schema name')
    if not schema_utils.is_valid_schema_description(description):
        return api.Error('bad_request', 'Invalid composed schema description')
    building_blocks = get_building_blocks(ctx)
    if not schema_utils.is_valid_blocks_list([list(block.keys())[0] for block in building_blocks], blocks):
        return api.Error('bad_request', 'Invalid schema building block list')

    # Verify schema exists before update.
    existing_schema = None
    for schema in get_composed_schemas(ctx):
        if schema["identifier"] == identifier:
            existing_schema = schema
            break

    if not existing_schema:
        return api.Error('not_found', 'Composed schema not found')

    # Block removal, all existing blocks must be present.
    existing_blocks = set(existing_schema.get("blocks", []))
    if not existing_blocks.issubset(set(blocks)):
        return api.Error('bad_request', 'Cannot remove blocks from existing schema')

    try:
        composed_schema = {
            "identifier": identifier,
            "name": name,
            "description": description,
            "blocks": blocks
        }
        zone = user.zone(ctx)
        avu.set_on_coll(ctx, f"/{zone}/yoda/composed_schemas", f"{constants.SCHEMA}_{identifier}", jsonutil.fast_dump(composed_schema))
    except Exception:
        return api.Error('internal', f"Failed to put composed schemas <{identifier}>")

    return api.Result.ok()


@api.make()
def api_schema_delete_composed_schema(ctx: rule.Context, identifier: str) -> api.Result:
    """A DELETE using ID for overview page to delete a composed schema.

    :param ctx:        Combined type of a callback and rei struct
    :param identifier: Composed metadata schema identifier

    :returns: Boolean indicating if composed schema is deleted
    """
    if not admin.is_admin(ctx, user.name(ctx)):
        return api.Error('not_allowed', 'Only admins can delete composed schemas')
    if not schema_utils.is_valid_schema_identifier(identifier):
        return api.Error('bad_request', 'Invalid composed schema identifier')

    if identifier in get_schema_ids_in_use(ctx):
        return api.Error('bad_request', 'Cannot delete a composed schema that is in use')

    try:
        zone = user.zone(ctx)
        avu.rmw_from_coll(ctx, f"/{zone}/yoda/composed_schemas", f"{constants.SCHEMA}_{identifier}", '%')
    except Exception:
        return api.Error('internal', f"Failed to delete composed schemas <{identifier}>")

    return api.Result.ok()


def build_composed_schema(ctx: rule.Context, identifier: str) -> Tuple[dict, dict]:
    """Build metadata schema from building blocks of a composed schema.

    :param ctx:        Combined type of a callback and rei struct
    :param identifier: Composed metadata schema identifier

    :returns: Metadata schema
    """
    if not schema_utils.is_valid_schema_identifier(identifier):
        return api.Error('bad_request', 'Invalid composed schema identifier')

    composed_schema = next(
        (item for item in get_composed_schemas(ctx)
         if item["identifier"] == identifier),
        None,
    )

    if composed_schema is None:
        return api.Error('not_found', 'Could not find composed schema with provided identifier')

    available_blocks = get_building_blocks(ctx)

    available_by_id = {
        block_id: block_data
        for item in available_blocks
        for block_id, block_data in item.items()
    }

    schemas = [
        available_by_id[block_ref]["schema"]
        for block_ref in composed_schema.get("blocks", [])
        if block_ref in available_by_id
    ]

    uischemas = [
        available_by_id[block_ref]["ui_schema"]
        for block_ref in composed_schema.get("blocks", [])
        if block_ref in available_by_id
    ]

    return schema_utils.merge_building_blocks(
        identifier=composed_schema["identifier"],
        title=composed_schema["name"],
        description=composed_schema["description"],
        schemas=schemas,
        uischemas=uischemas
    )


@api.make()
def api_schema_get_schemas(ctx: rule.Context) -> api.Result:
    """Retrieve selectable schemas, composed schemas, and default schema.

    :param ctx: Combined type of a callback and rei struct

    :returns: Dict with schemas, composed schemas, and default schema.
    """
    schemas = []

    iter = genquery.row_iterator(
        "COLL_NAME",
        f"COLL_PARENT_NAME = '/{user.zone(ctx)}/yoda/schemas' AND META_COLL_ATTR_NAME = '{constants.SCHEMA_USER_SELECTABLE}' AND META_COLL_ATTR_VALUE = 'True'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        schema = row[0].split('/')[-1]
        schemas.append(schema)

    composed_schemas = []
    for composed_schema in get_composed_schemas(ctx):
        composed_schemas.append(composed_schema['identifier'])

    if not config.default_yoda_schema:
        schema_default = ''
    else:
        schema_default = config.default_yoda_schema

    return {'schemas': schemas,
            'composed_schemas': composed_schemas,
            'schema_default': schema_default}


def get_schema_category_lookup_dict(ctx: rule.Context) -> defaultdict:
    """Returns a defaultdict that can be used to efficiently
       look up category- and environment-level metadata schemas
       of categories.

    :param ctx:        Combined type of a callback and rei struct

    :returns: defaultdict, where the default is the environment-level
              default metadata schema, and the keys/values are categories
              that have their own metadata schema. It will also return
              the environment-level default metadata schema for nonexistent
              categories.
    """
    # Function-level import to work around import dependency cycle
    # without major refactoring or code duplication.
    from groups import get_categories

    result = defaultdict(lambda: config.default_yoda_schema)
    categories = set(get_categories(ctx))
    schema_path = '/' + user.zone(ctx) + '/yoda/schemas'

    schema_collections = genquery.row_iterator(
        "COLL_NAME",
        f"DATA_NAME like 'metadata.json' AND COLL_NAME LIKE '{schema_path}/%'",
        genquery.AS_LIST, ctx
    )

    for schema_collection in schema_collections:
        name = schema_collection[0].split("/")[-1]
        if name in categories:
            result[name] = name

    return result


def get_schema_collection(ctx: rule.Context, rods_zone: str, group_name: str) -> str:
    """Determine schema collection based upon rods zone and name of the group.

    If there is no schema id set on group level and
    the category does not have a schema, 'default' is returned.

    :param ctx:        Combined type of a callback and rei struct
    :param rods_zone:  Rods zone name
    :param group_name: Group name

    :returns: string -- Category
    """
    schema_id = get_schema_id_from_group(ctx, group_name)
    if schema_id is not None:
        return schema_id

    # Find out category based on current group_name.
    category = '-1'
    iter = genquery.row_iterator(
        "META_USER_ATTR_NAME, META_USER_ATTR_VALUE",
        "USER_GROUP_NAME = '" + group_name + "' AND  META_USER_ATTR_NAME like 'category'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        category = row[1]

    if category != '-1':
        # Test whether found category actually has a metadata JSON.
        # If not, fall back to default schema collection.
        # /tempZone/yoda/schemas/default/metadata.json
        schema_path = '/' + rods_zone + '/yoda/schemas/' + category

        iter = genquery.row_iterator(
            "COLL_NAME",
            "DATA_NAME like 'metadata.json' AND COLL_NAME = '" + schema_path + "'",
            genquery.AS_LIST, ctx
        )

        for _row in iter:
            return category

    return config.default_yoda_schema


def get_schema_id_from_group(ctx: rule.Context, group_name: str) -> str | None:
    """Returns the schema_id value that has been set on an iRODS group

    :param ctx:        Combined type of a callback and rei struct
    :param group_name: Group name

    :returns:          Schema ID, or None if none is set.
    """
    iter = genquery.row_iterator(
        "META_USER_ATTR_VALUE",
        f"USER_NAME = '{group_name}' AND USER_TYPE = 'rodsgroup' AND META_USER_ATTR_NAME = 'schema_id'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        return row[0]

    return None


def get_active_schema_path(ctx: rule.Context, path: str) -> str:
    """Get the iRODS path to a schema file from a deposit, research or vault path.

    The schema collection is determined from group name of the path.

    :param ctx:   Combined type of a callback and rei struct
    :param path:  A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                  (anything after the group name is ignored)

    :returns: string -- Schema path (e.g. /tempZone/yoda/schemas/.../metadata.json)
    """
    path_parts = path.split('/')
    rods_zone  = path_parts[1]
    group_name = path_parts[3]

    # Metadata is updated in the vault, metadata is temporary stored in datamanager group.
    # e.g. /tempZone/home/datamanager-bla/vault-bla/pkg1[1667478959]/yoda-metadata.json
    if group_name.startswith("datamanager-"):
        group_name = path_parts[4]

    if group_name.startswith("vault-"):
        schema_coll = get_schema_id_from_group(ctx, group_name)
        if schema_coll is None:
            deposit_group_name = group_name.replace("vault-", "deposit-", 1)
            research_group_name = group_name.replace("vault-", "research-", 1)
            if group.exists(ctx, deposit_group_name):
                effective_group_name = deposit_group_name
            else:
                effective_group_name = research_group_name
            schema_coll = get_schema_collection(ctx, rods_zone, effective_group_name)
    else:
        schema_coll = get_schema_collection(ctx, rods_zone, group_name)

    return f'/{rods_zone}/yoda/schemas/{schema_coll}/metadata.json'


def get_active_schema(ctx: rule.Context, path: str) -> dict:
    """Get a schema object from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: Schema object (parsed from JSON)
    """
    schema = {}
    try:
        schema = jsonutil.read(ctx, get_active_schema_path(ctx, path))
    except Exception:
        path_parts = path.split('/')
        group_name = path_parts[3]
        composed_schema = get_schema_id_from_group(ctx, group_name)
        schema, _ = build_composed_schema(ctx, composed_schema)

    return schema


def get_active_schema_uischema(ctx: rule.Context, path: str) -> Tuple[dict, dict]:
    """Get a schema and uischema object from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: Schema and UI schema object (parsed from JSON)
    """
    schema = {}
    uischema = {}

    try:
        schema_path   = get_active_schema_path(ctx, path)
        uischema_path = f'{pathutil.chop(schema_path)[0]}/uischema.json'
        schema = jsonutil.read(ctx, schema_path)
        uischema = jsonutil.read(ctx, uischema_path)
    except Exception:
        path_parts = path.split('/')
        group_name = path_parts[3]
        composed_schema = get_schema_id_from_group(ctx, group_name)
        schema, uischema = build_composed_schema(ctx, composed_schema)

    return schema, uischema


def get_active_schema_id(ctx: rule.Context, path: str) -> str:
    """Get the active schema id from a research or vault path.

    :param ctx:  Combined type of a callback and rei struct
    :param path: A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                 (anything after the group name is ignored)

    :returns: string -- Schema $id (e.g. https://yoda.uu.nl/schemas/.../metadata.json)
    """
    return get_active_schema(ctx, path)['$id']


def get_schema_id(ctx: rule.Context, metadata_path: str, metadata: dict | None = None) -> str | None:
    """Get the current schema id from a path to a metadata json."""
    if metadata is None:
        metadata = jsonutil.read(ctx, metadata_path)
    return meta.metadata_get_schema_id(metadata)


def get_schema_path_by_id(ctx: rule.Context, path: str, schema_id: str) -> str | None:
    """Get a schema path from a schema id."""
    _, zone, _2, _3 = pathutil.info(path)

    # We do not fetch schemas from external sources, so for now assume that we
    # can find it using this pattern.
    m = re.match(r'https://yoda.uu.nl/schemas/([^/]+)/metadata.json', schema_id)
    if m:
        return f'/{zone}/yoda/schemas/{m.group(1)}/metadata.json'
    else:
        return None


def get_schema_by_id(ctx: rule.Context, path: str, schema_id: str) -> dict | None:
    """
    Get a schema from a schema id.

    The path is used solely to get the zone name.

    :param ctx:       Combined type of a callback and rei struct
    :param path:      A research or vault path, e.g. /tempZone/home/vault-bla/pkg1/yoda-metadata.json
                      (anything after the group name is ignored)
    :param schema_id: Identifier of schema to get

    :returns: Schema object (parsed from JSON)
    """
    schema_path = get_schema_path_by_id(ctx, path, schema_id)
    if schema_path is None:
        return None
    return jsonutil.read(ctx, schema_path)
