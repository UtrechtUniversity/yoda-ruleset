# \file      iiMetadataForm.py
# \brief     JSON metadata form handling
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# TODO: These belong in the uu/group manager part of our rulesets. {{{
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

def get_client_full_name_r(rule_args, callback, rei):
    """Obtain client name and zone, formatted as a 'x#y' string"""
    rule_args[0] = '{}#{}'.format(*get_client_name_zone(rei))

# }}}


def get_coll_org_metadata(callback, path):
    """Obtains a (k,v) list of all organisation metadata on a given collection"""

    return [(k,v) for k, v
                  in genquery.row_iterator("META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
                                           "COLL_NAME = '{}' AND META_COLL_ATTR_NAME like '{}%'"
                                            .format(path, UUORGMETADATAPREFIX),
                                           genquery.AS_LIST, callback)]

def get_coll_status(callback, path, org_metadata = None):
    """Get the status of a research folder."""

    if org_metadata is None:
       org_metadata = get_coll_org_metadata(callback, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if IISTATUSATTRNAME in org_metadata:
        return org_metadata[IISTATUSATTRNAME]
    return RESEARCH_PACKAGE_STATE['FOLDER']

def get_coll_vault_status(callback, path, org_metadata = None):
    """Get the status of a vault folder."""

    if org_metadata is None:
       org_metadata = get_coll_org_metadata(callback, path)

    # Don't care about duplicate attr names here.
    org_metadata = dict(org_metadata)
    if IIVAULTSTATUSATTRNAME in org_metadata:
        return org_metadata[IIVAULTSTATUSATTRNAME]
    return VAULT_PACKAGE_STATE['UNPUBLISHED']

def get_coll_lock(callback, path, org_metadata = None):
    """Check for existence of locks on a collection.
       path -> ((no|here|outoftree|ancestor|descendant), rootcoll)"""

    if org_metadata is None:
       org_metadata = get_coll_org_metadata(callback, path)

    ret = ('no', None)

    for root in [v for k, v in org_metadata if k == IILOCKATTRNAME]:
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


@rule(transform=json.dumps, handler=RuleOutput.STDOUT)
def iiMetadataFormLoad(callback, path):
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
                   'status',              # (folder status)
                   'lock_type',
                   'transformation_text', # ─── only if transformation needed
                   'errors',              # ─── only if errors present
                   'schema',              # ─┐
                   'uischema',            #  ├─ only if no errors and no transformation
                   'metadata']            # ─┘

    # Obtain some context.
    # - Who are we dealing with?
    # user = get_client_full_name(rei)
    user = callback.get_client_full_name_r('')['arguments'][0]

    # - What's kind of collection path is this?
    space, zone, group, subpath = get_path_info(path)
    if space not in [Space.RESEARCH, Space.VAULT]:
        return {}

    category = group_category(callback, group)

    # - What rights does the client have?
    is_member      = user_member_type(callback, group, user) in ['normal', 'manager']
    is_datamanager = user_is_datamanager(callback, category, user)

    # - What is the active schema for this category?
    schema, uischema = get_active_schema_uischema(callback, path)

    # Obtain org metadata for status and lock information.
    # (needed both for research and vault packages)
    org_metadata = get_coll_org_metadata(callback, path)

    if space is Space.RESEARCH:
        status = get_coll_status(callback, path, org_metadata)
        lock_type, lock_root = get_coll_lock(callback, path, org_metadata)

        # Analyze a possibly existing metadata JSON/XML file.

        meta_path = get_collection_metadata_path(callback, path)
        can_clone = False
        errors = []

        if meta_path is None:
            # If no metadata file exists, check if we can allow the user to
            # clone it from the parent collection.
            can_clone = bool(collection_has_cloneable_metadata(callback, chop_path(path)[0]))

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
                        path_out[-1] = '{} {}'.format(path_out[-1], x+1)
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
                metadata = read_json_object(callback, meta_path)
                current_schema_id = metadata_get_schema_id(metadata)
                if current_schema_id is None:
                    errors = ['Please check the structure of this file.']
            except UUJsonException as e:
                errors = ['Please check the structure of this file.']
            except UUMsiException as e:
                errors = ['The file could not be read.']

            if len(errors) > 0:
                del metadata, schema, uischema
            else:
                # Looks like a valid metadata file.
                # See if its schema is up to date.
                transform = get_transformation(callback, meta_path, metadata = metadata)

                if transform is None:
                    if current_schema_id == schema['$id']:
                        # Metadata matches active schema, see if it validates.
                        errors = [transform_error(x) for x
                                  in get_json_metadata_errors(callback,
                                                              meta_path,
                                                              metadata = metadata,
                                                              schema = schema,
                                                              ignore_required = True)]
                    else:
                        # Schema ID does not match and there is no defined transformation.
                        # We have no way to parse this file.
                        # XXX: Error message?
                        errors = ['Please check the structure of this file.']
                        callback.writeString('serverLog', 'Metadata file <{}> has untransformable schema <{}>'
                                                          .format(meta_path, current_schema_id))

                    if len(errors):
                        del metadata, schema, uischema
                else:
                    # Transformation is available. Do not load a metadata form.
                    # First, make sure that the current metadata is valid against its schema $id,
                    # if not, we cannot offer a transformation option.
                    try:
                        current_schema = get_schema_by_id(callback, meta_path, current_schema_id)
                        errors = [transform_error_path(x['path']) for x
                                  in get_json_metadata_errors(callback,
                                                              meta_path,
                                                              metadata = metadata,
                                                              schema = current_schema,
                                                              ignore_required = True)]
                    except Exception as e:
                        callback.writeString('serverLog',
                                             'Unknown error while validating <{}> against schema id <{}>: {}'
                                             .format(meta_path, current_schema_id, str(e)))
                        errors = ['Please check the structure of this file.']
                    else:
                        # No errors! Offer automatic transformation.
                        transformation_text = transformation_html(transform)

                    del metadata, schema, uischema

        elif meta_path.endswith('.xml'):
            # XXX: Prompt text?
            # (ask the user to perform conversion)
            transformation_text = '<p>Your yoda-metadata.xml needs to be converted to the new yoda-metadata.json format to continue.</p>'

    elif space is Space.VAULT:
        status = get_coll_vault_status(callback, path, org_metadata)
        meta_path = get_latest_vault_metadata_path(callback, path)

        # TODO

    # XXX Debug
    # print('-----')
    # for k, v in locals().items():
    #     if k not in output_keys: continue
    #     print('{} = {}'.format(k, v))
    # print('-----')

    return {k:v for k, v in locals().items() if k in output_keys}



def iiMetadataFormSave(rule_args, callback, rei):
    """Validate and store JSON metadata for a given collection."""

    # Reports status back to the caller.
    report = lambda x, y, z=[]: callback.writeString('stdout',
                                                     json.dumps({'status': x,
                                                                 'statusInfo': y,
                                                                 'errors': z}))

    coll, metadata_text = rule_args[:2]

    # Assume we are in the research area until proven otherwise.
    # (overwritten below in the vault case)
    is_vault = False
    json_path = '{}/{}'.format(coll, IIJSONMETADATA)

    m = re.match('^/([^/]+)/home/(vault-[^/]+)/(.+)$', coll)
    if m:
        # It's a vault path - set up a staging area in the datamanager collection.
        zone, vault_group, vault_subpath = m.groups()

        ret = callback.iiDatamanagerGroupFromVaultGroup(vault_group, '')
        datamanager_group = ret['arguments'][1]
        if datamanager_group == '':
            report('InternalError', 'could not get datamanager group')
            return

        tmp_coll = '/{}/home/{}/{}/{}'.format(zone, datamanager_group, vault_group, vault_subpath)

        try:
            coll_create(callback, tmp_coll, '1', irods_types.BytesBuf())
        except UUException as e:
            report('FailedToCreateCollection', 'Failed to create staging area at <{}>'.format(tmp_coll))
            return

        # Use staging area instead of trying to write to the vault directly.
        is_vault = True
        json_path = '{}/{}'.format(tmp_coll, IIJSONMETADATA)

    # Load form metadata input.
    try:
        metadata = parse_json(metadata_text)
    except UUException as e:
        # This should only happen if the form was tampered with.
        report('ValidationError', 'JSON decode error')
        return

    # Add metadata schema id to JSON.
    metadata_set_schema_id(metadata, get_active_schema_id(callback, json_path))

    # Validate JSON metadata.
    errors = get_json_metadata_errors(callback, json_path, metadata, ignore_required=not is_vault)

    if len(errors) > 0:
        report('ValidationError', 'Metadata validation failed', errors)
        return

    # No errors: write out JSON.
    try:
        write_data_object(callback, json_path, json.dumps(metadata, indent=4))
    except UUException as e:
        report('Error', 'Could not save yoda-metadata.json')
        return

    report('Success', '')
