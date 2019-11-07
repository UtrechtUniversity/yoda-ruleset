# -*- coding: utf-8 -*-
"""JSON metadata form handling."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
import genquery

import meta
import schema as schema_
import schema_transformation

from util import *

__all__ = ['api_uu_meta_form_load',
           'api_uu_meta_form_save']


# TODO: These belong in the group manager part of our rulesets. {{{
#       (and they should be plain python rules, not just wrappers for iRODS rules)

def group_category(callback, group):
    if group.startswith('vault-'):
        group = callback.uuGetBaseGroup(group, '')['arguments'][1]
    return callback.uuGroupGetCategory(group, '', '')['arguments'][1]


def user_member_type(callback, group, user):
    """returns: 'none' | 'reader' | 'normal' | 'manager'"""
    return callback.uuGroupGetMemberType(group, user, '')['arguments'][2]


def user_is_datamanager(callback, category, user):
    return user_member_type(callback, 'datamanager-{}'.format(category), user) \
        in ('normal', 'manager')


# }}}


def get_coll_org_metadata(callback, path):
    """Obtains a (k,v) list of all organisation metadata on a given collection"""

    return [(k, v) for k, v
            in genquery.row_iterator("META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                     "COLL_NAME = '{}' AND META_COLL_ATTR_NAME like '{}%'"
                                     .format(path, constants.UUORGMETADATAPREFIX),
                                     genquery.AS_LIST, callback)]


def get_coll_status(callback, path, org_metadata=None):
    """Get the status of a research folder."""

    if org_metadata is None:
        org_metadata = get_coll_org_metadata(callback, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if constants.IISTATUSATTRNAME in org_metadata:
        return org_metadata[constants.IISTATUSATTRNAME]
    return constants.RESEARCH_PACKAGE_STATE['FOLDER']


def get_coll_vault_status(callback, path, org_metadata=None):
    """Get the status of a vault folder."""

    if org_metadata is None:
        org_metadata = get_coll_org_metadata(callback, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if constants.IIVAULTSTATUSATTRNAME in org_metadata:
        return org_metadata[constants.IIVAULTSTATUSATTRNAME]
    return constants.VAULT_PACKAGE_STATE['UNPUBLISHED']


def get_coll_lock(callback, path, org_metadata=None):
    """Check for existence of locks on a collection.
       path -> ((no|here|outoftree|ancestor|descendant), rootcoll)"""

    if org_metadata is None:
        org_metadata = get_coll_org_metadata(callback, path)

    ret = ('no', None)

    for root in [v for k, v in org_metadata if k == constants.IILOCKATTRNAME]:
        if root == path:
            return 'here', root
        elif root.startswith(path):
            return 'descendant', root
        elif path.startswith(root):
            return 'ancestor', root
        else:
            # Keep searching, but write this lock down.
            ret = ('outoftree', root)

    return ret


@api.make()
def api_uu_meta_form_load(ctx, coll):
    """Retrieve all information required to load a metadata form
       in either the research or vault space.

       This produces a JSON struct on stdout. If no transformation is required
       and no errors prevent loading the form, the JSON will contain the
       schema, uischema and metadata.

       If a transformation is needed, this is indicated by the
       'transformation_text' string being present in the output.

       If errors prevent loading the form, or if errors make a transformation
       impossible, this is indicated by the 'errors' array being present in the
       output.
    """
    # The information that is returned to the caller, in dict form.
    output_keys = ['is_member',
                   'is_datamanager',
                   'can_clone',
                   'status',               # (folder status)
                   'lock_type',
                   'transformation_text',  # ─── only if transformation needed
                   'errors',               # ─── only if errors present
                   'schema',               # ─┐
                   'uischema',             #  ├─ only if no errors and no transformation
                   'metadata']             # ─┘

    # Obtain some context.
    # - Who are we dealing with?
    user_full_name = user.full_name(ctx)

    # - What's kind of collection path is this?
    space, zone, group, subpath = pathutil.info(coll)
    if space not in [pathutil.Space.RESEARCH, pathutil.Space.VAULT]:
        return {}

    category = group_category(ctx, group)

    # - What rights does the client have?
    is_member      = user_member_type(ctx, group, user_full_name) in ['normal', 'manager']
    is_datamanager = user_is_datamanager(ctx, category, user_full_name)

    # - What is the active schema for this category?
    schema, uischema = schema_.get_active_schema_uischema(ctx, coll)

    # Obtain org metadata for status and lock information.
    # (needed both for research and vault packages)
    org_metadata = get_coll_org_metadata(ctx, coll)

    if space is pathutil.Space.RESEARCH:
        status = get_coll_status(ctx, coll, org_metadata)
        lock_type, lock_root = get_coll_lock(ctx, coll, org_metadata)

        # Analyze a possibly existing metadata JSON/XML file.

        meta_path = meta.get_collection_metadata_path(ctx, coll)
        can_clone = False
        errors = []

        if meta_path is None:
            # If no metadata file exists, check if we can allow the user to
            # clone it from the parent collection.
            can_clone = bool(meta.collection_has_cloneable_metadata(ctx, pathutil.chop(coll)[0]))

        elif meta_path.endswith('.json'):
            # Metadata file is in the correct format. Try to validate it.

            # Old error format:
            # - Creator[0].Person_Identifier[0].Name_Identifier_Scheme
            # New error format:
            # - Creator 1 -> Person Identifier 1 -> Name Identifier Scheme
            def transform_error(e):
                # Make array indices human-readable.
                path_out = []
                for i, x in enumerate(e['path']):
                    if type(x) is int:
                        path_out[-1] = '{} {}'.format(path_out[-1], x + 1)
                    else:
                        path_out += [x.replace('_', ' ')]

                # Get the names of disallowed extra fields.
                # (the jsonschema library isn't of much help here - we must extract it from the message)
                if e['validator'] == u'additionalProperties' and len(path_out) == 0:
                    m = re.search('[\'\"]([^\"\']+)[\'\"] was unexpected', e['message'])
                    if m:
                        return 'This extra field is not allowed: ' + m.group(1)
                    else:
                        return 'Extra fields are not allowed'
                else:
                    return 'This field contains an error: ' + ' -> '.join(path_out)

            # Try to load the metadata file.
            metadata = dict()
            try:
                metadata = jsonutil.read(ctx, meta_path)
                current_schema_id = meta.metadata_get_schema_id(metadata)
                if current_schema_id is None:
                    errors = ['Please check the structure of this file.']
            except jsonutil.ParseError as e:
                errors = ['Please check the structure of this file.']
            except msi.Error as e:
                errors = ['The file could not be read.']

            if len(errors) > 0:
                del metadata, schema, uischema
            else:
                # Looks like a valid metadata file.
                # See if its schema is up to date.
                transform = schema_transformation.get(ctx, meta_path, metadata=metadata)

                if transform is None:
                    if current_schema_id == schema['$id']:
                        # Metadata matches active schema, see if it validates.
                        errors = [transform_error(x) for x
                                  in meta.get_json_metadata_errors(ctx,
                                                                   meta_path,
                                                                   metadata=metadata,
                                                                   schema=schema,
                                                                   ignore_required=True)]
                    else:
                        # Schema ID does not match and there is no defined transformation.
                        # We have no way to parse this file.
                        # XXX: Error message?
                        errors = ['Please check the structure of this file.']
                        log.write(ctx, 'Metadata file <{}> has untransformable schema <{}> (need {})'
                                  .format(meta_path, current_schema_id, schema['$id']))

                    if len(errors):
                        del metadata, schema, uischema
                else:
                    # Transformation is available. Do not load a metadata form.
                    # First, make sure that the current metadata is valid against its schema $id,
                    # if not, we cannot offer a transformation option.
                    try:
                        current_schema = schema_.get_schema_by_id(ctx, meta_path, current_schema_id)
                        errors = [transform_error(x) for x
                                  in meta.get_json_metadata_errors(ctx,
                                                                   meta_path,
                                                                   metadata=metadata,
                                                                   schema=current_schema,
                                                                   ignore_required=True)]
                    except Exception as e:
                        log.write(ctx, 'Unknown error while validating <{}> against schema id <{}>: {}'
                                  .format(meta_path, current_schema_id, str(e)))
                        errors = ['Please check the structure of this file.']
                    else:
                        # No errors! Offer automatic transformation.
                        transformation_text = schema_transformation.html(transform)

                    del metadata, schema, uischema

        elif meta_path.endswith('.xml'):
            # XXX: Prompt text?
            # (ask the user to perform conversion)
            transformation_text = '<p>Your yoda-metadata.xml needs to be converted to the new yoda-metadata.json format to continue.</p>'

    elif space is pathutil.Space.VAULT:
        status = get_coll_vault_status(ctx, coll, org_metadata)
        meta_path = get_latest_vault_metadata_path(ctx, coll)

        # TODO

    return {k: v for k, v in locals().items() if k in output_keys}


@api.make()
def api_uu_meta_form_save(ctx, collection, metadata):
    """Validate and store JSON metadata for a given collection."""

    coll = '/{}/home{}'.format(user.zone(ctx), collection)

    log.write(ctx, 'save form for coll <{}>'.format(coll))

    # Assume we are in the research area until proven otherwise.
    # (overwritten below in the vault case)
    is_vault = False
    json_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    m = re.match('^/([^/]+)/home/(vault-[^/]+)/(.+)$', coll)
    if m:
        # It's a vault path - set up a staging area in the datamanager collection.
        zone, vault_group, vault_subpath = m.groups()

        ret = ctx.iiDatamanagerGroupFromVaultGroup(vault_group, '')
        datamanager_group = ret['arguments'][1]
        if datamanager_group == '':
            return api.Error('internal', 'could not get datamanager group')

        tmp_coll = '/{}/home/{}/{}/{}'.format(zone, datamanager_group, vault_group, vault_subpath)

        try:
            msi.coll_create(ctx, tmp_coll, '1', irods_types.BytesBuf())
        except error.UUError as e:
            return api.Error('coll_create', 'Failed to create staging area at <{}>'.format(tmp_coll))

        # Use staging area instead of trying to write to the vault directly.
        is_vault = True
        json_path = '{}/{}'.format(tmp_coll, constants.IIJSONMETADATA)

    # Add metadata schema id to JSON.
    meta.metadata_set_schema_id(metadata, schema_.get_active_schema_id(ctx, json_path))

    # Validate JSON metadata.
    errors = meta.get_json_metadata_errors(ctx, json_path, metadata, ignore_required=not is_vault)

    if len(errors) > 0:
        return api.Error('validation', 'Metadata validation failed', data={'errors': errors})

    # No errors: write out JSON.
    try:
        data_object.write(ctx, json_path, jsonutil.dump(metadata, indent=4))
    except error.UUError as e:
        return api.Error('internal', 'Could not save yoda-metadata.json')
