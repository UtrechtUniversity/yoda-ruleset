# -*- coding: utf-8 -*-
"""JSON metadata form handling."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

import irods_types

import folder
import meta
import schema as schema_
import schema_transformation
import vault
from util import *

__all__ = ['api_meta_form_load',
           'api_meta_form_save']


# TODO: These belong in the group manager part of our rulesets. {{{
#       (and they should be plain python rules, not just wrappers for iRODS rules)
#
# Since a group manager overhaul is pending, this is left as it is for now.

def group_category(ctx, group):
    if group.startswith('vault-'):
        group = ctx.uuGetBaseGroup(group, '')['arguments'][1]
    return ctx.uuGroupGetCategory(group, '', '')['arguments'][1]


def user_member_type(ctx, group, user):
    """returns: 'none' | 'reader' | 'normal' | 'manager'"""
    return ctx.uuGroupGetMemberType(group, user, '')['arguments'][2]


def user_is_datamanager(ctx, category, user):
    return user_member_type(ctx, 'datamanager-{}'.format(category), user) \
        in ('normal', 'manager')


# }}}


def get_coll_lock(ctx, path, org_metadata=None):
    """Check for existence of locks on a collection.

    path -> ((no|here|outoftree|ancestor|descendant), rootcoll)

    :param ctx:          Combined type of a callback and rei struct
    :param path:         Path of collection to check for locks
    :param org_metadata: Organizational metadata of folder

    :returns: Locks on collection
    """
    if org_metadata is None:
        org_metadata = folder.get_org_metadata(ctx, path)

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


def get_coll_lock_count(ctx, path, org_metadata=None):
    """Count locks on a collection.

    :param ctx:          Combined type of a callback and rei struct
    :param path:         Path of collection to count locks on
    :param org_metadata: Organizational metadata of folder

    :returns: Number of locks on collection
    """
    if org_metadata is None:
        org_metadata = folder.get_org_metadata(ctx, path)

    count = 0

    for _root in [v for k, v in org_metadata if k == constants.IILOCKATTRNAME]:
        count += 1

    return count


def humanize_validation_error(e):
    """Transform a jsonschema validation error such that it is readable by humans.

    :param e: a jsonschema.exceptions.ValidationError

    :returns: a supposedly human-readable description of the error
    """
    # Error format: "Creator 1 -> Person Identifier 1 -> Name Identifier Scheme"

    # Make array indices human-readable.
    path_out = []
    for _i, x in enumerate(e['path']):
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


@api.make()
def api_meta_form_load(ctx, coll):
    """Retrieve all information required to load a metadata form in either the research or vault space.

    This produces a JSON struct on stdout. If no transformation is required
    and no errors prevent loading the form, the JSON will contain the
    schema, uischema and metadata.

    If a transformation is needed, this is indicated by the
    'transformation_text' string being present in the output.

    If errors prevent loading the form, or if errors make a transformation
    impossible, this is indicated by the 'errors' array being present in the
    output.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Collection to retrieve all information required to load a metadata form from

    :returns: API status
    """
    can_edit  = False
    can_clone = False
    is_locked = False
    metadata  = None
    errors    = []

    # Obtain some context.
    # - Who are we dealing with?
    user_full_name = user.full_name(ctx)

    # - What kind of collection path is this?
    space, zone, group, subpath = pathutil.info(coll)
    if space not in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT, pathutil.Space.VAULT]:
        return {}

    category = group_category(ctx, group)

    # - What rights does the client have?
    is_member = user_member_type(ctx, group, user_full_name) in ['normal', 'manager']

    # - What is the active schema for this category?
    schema, uischema = schema_.get_active_schema_uischema(ctx, coll)

    # Obtain org metadata for status and lock information.
    # (needed both for research and vault packages)
    org_metadata = folder.get_org_metadata(ctx, coll)

    if space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        is_locked = folder.is_locked(ctx, coll, org_metadata)
        can_edit = is_member and not is_locked

        # Analyze a possibly existing metadata JSON file.
        meta_path = meta.get_collection_metadata_path(ctx, coll)

        if meta_path is None:
            # If no metadata file exists, check if we can allow the user to
            # clone it from the parent collection.
            can_clone = bool(meta.collection_has_cloneable_metadata(ctx, pathutil.chop(coll)[0]))

        elif meta_path.endswith('.json'):
            # Metadata file is in the correct format. Try to validate it.

            # Try to load the metadata file.
            try:
                metadata = jsonutil.read(ctx, meta_path)
                current_schema_id = meta.metadata_get_schema_id(metadata)
                if current_schema_id is None:
                    return api.Error('no_schema_id', 'Please check the structure of this file.',
                                     'schema id missing')
            except jsonutil.ParseError:
                return api.Error('bad_json', 'Please check the structure of this file.', 'JSON invalid')
            except msi.Error as e:
                return api.Error('internal', 'The metadata file could not be read.', e)

            # Looks like a valid metadata file.
            # See if its schema is up to date.
            transform = schema_transformation.get(ctx, meta_path, metadata=metadata)

            if transform is not None:
                # Transformation is available & required. Do not load a metadata form.
                # First, make sure that the current metadata is valid against its schema $id,
                # if not, we cannot offer a transformation option.
                try:
                    current_schema = schema_.get_schema_by_id(ctx, meta_path, current_schema_id)
                    errors = [humanize_validation_error(x) for x
                              in meta.get_json_metadata_errors(ctx,
                                                               meta_path,
                                                               metadata=metadata,
                                                               schema=current_schema,
                                                               ignore_required=True)]
                    if errors:
                        return api.Error('validation', 'The metadata file is not compliant with the schema.',
                                         data={'errors': errors})
                except Exception as e:
                    log.write(ctx, 'Unknown error while validating <{}> against schema id <{}>: {}'
                              .format(meta_path, current_schema_id, str(e)))
                    return api.Error('internal', 'The metadata file is could not be validated due to an internal error.')
                else:
                    # No errors! Offer automatic transformation.
                    return api.Error('transformation_needed',
                                     'The metadata file needs to be transformed to the new schema to continue.',
                                     data={'transformation_html': schema_transformation.html(transform),
                                           'can_edit': can_edit})

            if current_schema_id == schema['$id']:
                # Metadata matches active schema, see if it validates.
                errors = [humanize_validation_error(x) for x
                          in meta.get_json_metadata_errors(ctx,
                                                           meta_path,
                                                           metadata=metadata,
                                                           schema=schema,
                                                           ignore_required=True)]
                if errors:
                    return api.Error('validation', 'The metadata file is not compliant with the schema.',
                                     data={'errors': errors})
            else:
                # Schema ID does not match and there is no defined transformation.
                # We have no way to parse this file.
                log.write(ctx, 'Metadata file <{}> has untransformable schema <{}> (need {})'
                               .format(meta_path, current_schema_id, schema['$id']))
                return api.Error('bad_schema',
                                 'The metadata file is not compliant with the schema in this category and cannot be transformed. '
                                 + 'Please contact your datamanager.')

    elif space is pathutil.Space.VAULT:
        status    = vault.get_coll_vault_status(ctx, coll, org_metadata)
        can_edit  = (user_is_datamanager(ctx, category, user_full_name)
                     and (status == constants.vault_package_state.UNPUBLISHED
                          or status == constants.vault_package_state.PUBLISHED
                          or status == constants.vault_package_state.DEPUBLISHED))
        meta_path = meta.get_latest_vault_metadata_path(ctx, coll)

        # Try to load the metadata file.
        try:
            metadata = jsonutil.read(ctx, meta_path)
            current_schema_id = meta.metadata_get_schema_id(metadata)
            if current_schema_id is None:
                return api.Error('no_schema_id', 'Please check the structure of this file.',
                                 'schema id missing')
        except jsonutil.ParseError:
            return api.Error('bad_json', 'Please check the structure of this file.', 'JSON invalid')
        except msi.Error as e:
            return api.Error('internal', 'The metadata file could not be read.', e)

        if current_schema_id == schema['$id']:
            # Metadata matches active schema, see if it validates.
            errors = [humanize_validation_error(x) for x
                      in meta.get_json_metadata_errors(ctx,
                                                       meta_path,
                                                       metadata=metadata,
                                                       schema=schema,
                                                       ignore_required=True)]
            if errors:
                return api.Error('validation', 'The metadata file is not compliant with the schema.',
                                 data={'errors': errors})
        else:
            # Schema ID does not match and there is no defined transformation.
            # We have no way to parse this file.
            log.write(ctx, 'Metadata file <{}> has untransformable schema <{}> (need {})'
                           .format(meta_path, current_schema_id, schema['$id']))
            return api.Error('bad_schema',
                             'The metadata file is not compliant with the schema in this category and cannot be transformed. '
                             + 'Please contact your datamanager.')

    return {'can_edit': can_edit,
            'can_clone': can_clone,
            'schema': schema,
            'uischema': uischema,
            'metadata': metadata,
            'is_locked': is_locked}


@api.make()
def api_meta_form_save(ctx, coll, metadata):
    """Validate and store JSON metadata for a given collection.

    :param ctx:      Combined type of a callback and rei struct
    :param coll:     Collection to save metadata on
    :param metadata: Metadata to save

    :returns: API status
    """
    log.write(ctx, 'save form for coll <{}>'.format(coll))

    json_path = '{}/{}'.format(coll, constants.IIJSONMETADATA)

    space, zone, group, subpath = pathutil.info(coll)
    is_vault = space is pathutil.Space.VAULT
    if is_vault:
        # It's a vault path - set up a staging area in the datamanager collection.

        ret = ctx.iiDatamanagerGroupFromVaultGroup(group, '')
        datamanager_group = ret['arguments'][1]
        if datamanager_group == '':
            return api.Error('internal', 'could not get datamanager group')

        tmp_coll = '/{}/home/{}/{}/{}'.format(zone, datamanager_group, group, subpath)

        try:
            msi.coll_create(ctx, tmp_coll, '1', irods_types.BytesBuf())
        except error.UUError:
            return api.Error('coll_create', 'Failed to create staging area at <{}>'.format(tmp_coll))

        # Use staging area instead of trying to write to the vault directly.
        json_path = '{}/{}'.format(tmp_coll, constants.IIJSONMETADATA)

    # Add metadata schema id to JSON.
    meta.metadata_set_schema_id(metadata, schema_.get_active_schema_id(ctx, json_path))

    # Validate JSON metadata.
    errors = meta.get_json_metadata_errors(ctx, json_path, metadata, ignore_required=not is_vault)

    if len(errors) > 0:
        return api.Error('validation', 'Metadata validation failed', data={'errors': errors})

    # No errors: write out JSON.
    try:
        jsonutil.write(ctx, json_path, metadata)
    except error.UUError:
        return api.Error('internal', 'Could not save yoda-metadata.json')
