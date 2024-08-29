# -*- coding: utf-8 -*-
"""Functions for handling schema updates within any yoda-metadata file."""

__copyright__ = 'Copyright (c) 2018-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_transform_vault_metadata',
           'rule_batch_vault_metadata_correct_orcid_format',
           'rule_batch_vault_metadata_schema_report',
           'rule_get_transformation_info',
           'api_transform_metadata',
           'rule_batch_vault_packages_troubleshoot',
           'rule_batch_vault_packages_troubleshoot3',
           'rule_batch_vault_packages_troubleshoot4',
           'rule_batch_find_published_data_packages',]

import json
import os
import re
import time

import genquery
import session_vars

import meta
import meta_form
import schema
import schema_transformations
from util import *


def execute_transformation(ctx, metadata_path, transform, keep_metadata_backup=True):
    """Transform a metadata file with the given transformation function."""
    coll, data = os.path.split(metadata_path)

    group_name = metadata_path.split('/')[3]

    metadata = jsonutil.read(ctx, metadata_path)
    metadata = transform(ctx, metadata)

    # make_metadata_backup is only relevant for research
    if group_name.startswith('research-'):
        if keep_metadata_backup:
            backup = '{}/transformation-backup[{}].json'.format(coll, str(int(time.time())))
            data_object.copy(ctx, metadata_path, backup)
        jsonutil.write(ctx, metadata_path, metadata)
    elif group_name.startswith('vault-'):
        new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
        # print('TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
        jsonutil.write(ctx, new_path, metadata)
        copy_acls_from_parent(ctx, new_path, "default")
        ctx.rule_provenance_log_action("system", coll, "updated metadata schema")
        log.write(ctx, "Transformed %s" % (new_path))
    else:
        raise AssertionError()


@api.make()
def api_transform_metadata(ctx, coll, keep_metadata_backup=True):
    """Transform a yoda-metadata file in the given collection to the active schema."""
    metadata_path = meta.get_collection_metadata_path(ctx, coll)
    if metadata_path.endswith('.json'):
        # JSON metadata.
        log.write(ctx, 'Transforming JSON metadata in the research space: <{}>'.format(metadata_path))
        transform = get(ctx, metadata_path)

        if transform is None:
            return api.Error('undefined_transformation', 'No transformation found')

        execute_transformation(ctx, metadata_path, transform, keep_metadata_backup)
    else:
        return api.Error('no_metadata', 'No metadata file found')


def get(ctx, metadata_path, metadata=None):
    """Find a transformation that can be executed on the given metadata JSON.

    :param ctx:           Combined type of a ctx and rei struct
    :param metadata_path: Path to metadata JSON
    :param metadata:      Optional metadata object

    :returns: Transformation function on success, or None if no transformation was found
    """
    try:
        src = schema.get_schema_id(ctx, metadata_path, metadata=metadata)
        dst = schema.get_active_schema_id(ctx, metadata_path)

        # Ideally, we would check that the metadata is valid in its current
        # schema before claiming that we can transform it...

        # print('{} -> {}'.format(src,dst))

        return schema_transformations.get(src, dst)
    except KeyError:
        return None
    except error.UUError:
        # print('{} -> {} ERR {}'.format(src,dst, e))
        return None


# TODO: @rule.make
def rule_get_transformation_info(rule_args, callback, rei):
    """Check if a yoda-metadata.json transformation is possible and if so, retrieve transformation description.

    :param rule_args: [0] JSON path
                      [1] Transformation possible? true|false
                      [2] human-readable description of the transformation
    :param callback:  Callback to rule Language
    :param rei:       The rei struct

    """
    json_path = rule_args[0]

    rule_args[1:3] = 'false', ''

    transform = get(callback, json_path)

    if transform is not None:
        rule_args[1:3] = 'true', transformation_html(transform)


def copy_acls_from_parent(ctx, path, recursive_flag):
    """
    When inheritance is missing we need to copy ACLs when introducing new data in vault package.

    :param ctx:            Combined type of a ctx and rei struct
    :param path:           Path of object that needs the permissions of parent
    :param recursive_flag: Either "default" for no recursion or "recursive"
    """
    parent = os.path.dirname(path)

    iter = genquery.row_iterator(
        "COLL_ACCESS_NAME, COLL_ACCESS_USER_ID",
        "COLL_NAME = '" + parent + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        access_name = row[0]
        user_id = int(row[1])

        user_name = user.name_from_id(ctx, user_id)

        # iRODS keeps ACLs for deleted users in the iCAT database (https://github.com/irods/irods/issues/7778),
        # so we need to skip ACLs referring to users that no longer exist.
        if user_name == "":
            continue

        if access_name == "own":
            log.write(ctx, "iiCopyACLsFromParent: granting own to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "own", user_name, path)
        elif access_name == "read object":
            log.write(ctx, "iiCopyACLsFromParent: granting read to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "read", user_name, path)
        elif access_name == "modify object":
            log.write(ctx, "iiCopyACLsFromParent: granting write to <" + user_name + "> on <" + path + "> with recursiveFlag <" + recursive_flag + ">")
            msi.set_acl(ctx, recursive_flag, "write", user_name, path)


# TODO: @rule.make
def rule_batch_transform_vault_metadata(rule_args, callback, rei):
    """
    Transform all metadata JSON files in the vault to the active schema.

    :param rule_args: [0] First COLL_ID to check - initial = 0
                      [1] Batch size, <= 256
                      [2] Pause between checks (float)
                      [3] Delay between batches in seconds
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
    """
    coll_id = int(rule_args[0])
    batch   = int(rule_args[1])
    pause   = float(rule_args[2])
    delay   = int(rule_args[3])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one batch of metadata schemas.

    # Find all research and vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_NAME like 'yoda-metadata%%json' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        genquery.AS_LIST, callback)

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        path_parts = coll_name.split('/')

        # Only process collections that are directly beneath the apex
        # vault collection, e.g. /zoneName/home/vault-foo/data-package[123],
        # since metadata in the original part of the data package should not
        # be processed.
        if not re.match(r"^\/[^\/]+\/home\/[^\/]+\/[^\/]+$", coll_name):
            continue

        try:
            # Get vault package path.
            vault_package = '/'.join(path_parts[:5])
            metadata_path = meta.get_latest_vault_metadata_path(callback, vault_package)
            log.write(callback, "[METADATA] Checking whether metadata needs to be transformed: " + metadata_path)
            if metadata_path  != '':
                transform = get(callback, metadata_path)
                if transform is not None:
                    log.write(callback, "[METADATA] Executing transformation for: " + metadata_path)
                    execute_transformation(callback, metadata_path, transform)
        except Exception as e:
            log.write(callback, "[METADATA] Exception occurred during schema transformation of %s: %s" % (coll_name, str(type(e)) + ":" + str(e)))

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id += 1
    else:
        # All done.
        coll_id = 0
        log.write(callback, "[METADATA] Finished updating metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_transform_vault_metadata('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


# TODO: @rule.make
def rule_batch_vault_metadata_correct_orcid_format(rule_args, callback, rei):
    """
    Correct ORCID person identifier with invalid format in metadata JSON files in the vault.

    :param rule_args: [0] First COLL_ID to check - initial = 0
                      [1] Batch size, <= 256
                      [2] Pause between checks (float)
                      [3] Delay between batches in seconds
                      [4] Dry-run mode ('true' or 'false'; everything else is considered 'false')
    :param callback:  Callback to rule Language
    :param rei:       The rei struct
    """

    coll_id = int(rule_args[0])
    batch   = int(rule_args[1])
    pause   = float(rule_args[2])
    delay   = int(rule_args[3])
    dryrun_mode = rule_args[4] == "true"
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one batch of metadata schemas.

    # Find all vault collections, ordered by COLL_ID.
    iter = genquery.row_iterator(
        "ORDER(COLL_ID), COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND COLL_NAME not like '%%/original' AND DATA_NAME like 'yoda-metadata%%json' AND COLL_ID >= '%d'" % (rods_zone, coll_id),
        genquery.AS_LIST, callback)

    # Check each collection in batch.
    for row in iter:
        coll_id = int(row[0])
        coll_name = row[1]
        path_parts = coll_name.split('/')

        try:
            # Get vault package path.
            vault_package = '/'.join(path_parts[:5])
            metadata_path = meta.get_latest_vault_metadata_path(callback, vault_package)
            if metadata_path  != '':
                metadata = jsonutil.read(callback, metadata_path)

                # We only need to transform metadata with schemas that do not constrain ORCID format
                license_url = metadata.get("links", {})[0].get("href", "")
                license = license_url.replace("https://yoda.uu.nl/schemas/", "").replace("/metadata.json", "")
                if license not in ['core-1', 'core-2', 'default-1', 'default-2', 'default-3', 'hptlab-1', 'teclab-1', 'dag-0', 'vollmer-0']:
                    log.write(callback, "Skipping data package '%s' for ORCID transformation because license '%s' is excluded."
                              % (vault_package, license))
                    continue

                # Correct the incorrect orcid(s) if possible
                # result is a dict containing 'data_changed' 'metadata'
                result = transform_orcid(callback, metadata)

                # In order to minimize changes within the vault only save a new metadata.json if there actually has been at least one orcid correction.
                if result['data_changed'] and not dryrun_mode:
                    # orcid('s) has/have been adjusted. Save the changes in the same manner as execute_transformation for vault packages.
                    coll, data = os.path.split(metadata_path)
                    new_path = '{}/yoda-metadata[{}].json'.format(coll, str(int(time.time())))
                    log.write(callback, 'TRANSFORMING in vault <{}> -> <{}>'.format(metadata_path, new_path))
                    jsonutil.write(callback, new_path, result['metadata'])
                    copy_acls_from_parent(callback, new_path, "default")
                    callback.rule_provenance_log_action("system", coll, "updated person identifier metadata")
                    log.write(callback, "Transformed ORCIDs for: %s" % (new_path))
                elif result['data_changed']:
                    log.write(callback, "Would have transformed ORCIDs for: %s if dry run mode was disabled." % (metadata_path))

        except Exception as e:
            log.write(callback, "Exception occurred during ORCID transformation of %s: %s" % (coll_name, str(type(e)) + ":" + str(e)))

        # Sleep briefly between checks.
        time.sleep(pause)

        # The next collection to check must have a higher COLL_ID.
        coll_id += 1
    else:
        # All done.
        coll_id = 0
        log.write(callback, "[METADATA] Finished correcting ORCID's within vault metadata.")

    if coll_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<INST_NAME>irods_rule_engine_plugin-irods_rule_language-instance</INST_NAME><PLUSET>%ds</PLUSET>" % delay,
            "rule_batch_vault_metadata_correct_orcid_format('%d', '%d', '%f', '%d')" % (coll_id, batch, pause, delay),
            "")


def transform_orcid(ctx, m):
    """
    Transform all present orcid's into the correct format. If possible!

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform

    :returns: Dict with indication whether data has changed and transformed JSON object with regard to ORCID
    """
    data_changed = False

    # Only Creators and Contributors hold Person identifiers that can hold ORCIDs.
    for pi_holder in ['Creator', 'Contributor']:
        if m.get(pi_holder, False):
            for holder in m[pi_holder]:
                for pi in holder.get('Person_Identifier', dict()):
                    if pi.get('Name_Identifier_Scheme', None)  == 'ORCID':
                        # If incorrect ORCID format => try to correct.
                        if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", pi.get('Name_Identifier', None)):
                            original_orcid = pi['Name_Identifier']
                            corrected_orcid = correctify_orcid(original_orcid)
                            # Only it an actual correction took place change the value and mark this data as 'changed'.
                            if corrected_orcid is None:
                                log.write(ctx, "Warning: unable to automatically fix ORCID '%s'" % (original_orcid))
                            elif corrected_orcid != original_orcid:
                                log.write(ctx, "Updating ORCID '%s' to '%s'" % (original_orcid, corrected_orcid))
                                pi['Name_Identifier'] = corrected_orcid
                                data_changed = True

    return {'metadata': m, 'data_changed': data_changed}


def correctify_orcid(org_orcid):
    """Function to correct illformatted ORCIDs. Returns None if value cannot be fixed."""
    # Get rid of all spaces.
    orcid = org_orcid.replace(' ', '')

    # Upper-case X.
    orcid = org_orcid.replace('x', 'X')

    # The last part should hold a valid id like eg: 1234-1234-1234-123X.
    # If not, it is impossible to correct it to the valid orcid format
    orcs = orcid.split('/')
    if not re.search("^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcs[-1]):
        return None

    return "https://orcid.org/{}".format(orcs[-1])


def html(f):
    """Get a human-readable HTML description of a transformation function.

    The text is derived from the function's docstring.

    :param f: Transformation function

    :returns: Human-readable HTML description of a transformation function
    """
    description = '\n'.join(map(lambda paragraph:
                            '<p>{}</p>'.format(  # Trim whitespace.
                                re.sub('\s+', ' ', paragraph).strip()),
                                # Docstring paragraphs are separated by blank lines.
                                re.split('\n{2,}', f.__doc__)))

    # Remove docstring.
    description = re.sub('((:param).*)|((:returns:).*)', ' ', description)

    return description


@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_metadata_schema_report(ctx):
    """Show vault metadata schema about each data package in vault

    :param ctx:      Combined type of a callback and rei struct

    :returns:        JSON-encoded dictionary, where each key is a vault data package path.
                     Values are dictionaries with keys "schema" (contains the short name of the schema
                     (e.g. 'default-3', as per the information in the metadata file, or empty if no metadata
                     schema could be found), and match_schema (contains a boolean value that indicates whether
                     the metadata matches the JSON schema). match_schema only has a meaning if a metadata schema
                     could be found.
    """
    results = dict()
    schema_cache = dict()
    print("schema_cache_initial",schema_cache)

    # Find all vault collections
    iter = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '/%s/home/vault-%%' AND COLL_NAME not like '%%/original' AND COLL_NAME NOT LIKE '%%/original/%%' AND DATA_NAME like 'yoda-metadata%%json'" %
        (user.zone(ctx)),
        genquery.AS_LIST, ctx)

    for row in iter:
        coll_name = row[0]
        metadata_path = meta.get_latest_vault_metadata_path(ctx, coll_name)

        if metadata_path == '' or metadata_path is None:
            log.write(ctx, "Vault metadata schema report skips %s, because metadata could not be found."
                           % (coll_name))
            continue

        try:
            metadata = jsonutil.read(ctx, metadata_path)
        except Exception as exc:
            log.write(ctx, "Vault metadata report skips %s, because of exception while reading metadata file %s: %s."
                           % (coll_name, metadata_path, str(exc)))
            continue

        # Determine schema
        schema_id = schema.get_schema_id(ctx, metadata_path)
        print("the retrived schema id of metadata_path,schema_id ",metadata_path,schema_id)

        schema_shortname = schema_id.split("/")[-2]
        print("the shortname schema, ",schema_shortname)

        # Retrieve schema and cache it for future use
        schema_path = schema.get_schema_path_by_id(ctx, metadata_path, schema_id)
        print("the schema_path, ",schema_path)
        print("schema_cache",schema_cache)
        if schema_shortname in schema_cache:
            schema_contents = schema_cache[schema_shortname]
        else:
            schema_contents = jsonutil.read(ctx, schema_path)
            schema_cache[schema_shortname] = schema_contents

        # Check whether metadata matches schema and log any errors
        print("checking metadata_path: {},\n metadata:{},\n schema:{} ".format(metadata_path, metadata, schema_contents))
        error_list = meta.get_json_metadata_errors(ctx, metadata_path, metadata=metadata, schema=schema_contents)
        match_schema = len(error_list) == 0
        if not match_schema:
            log.write(ctx, "Vault metadata schema report: metadata %s did not match schema %s: %s" %
                           (metadata_path, schema_shortname, str([meta_form.humanize_validation_error(e).encode('utf-8') for e in error_list])))

        # Update results FIXME: do not update yet
        results[coll_name] = {"schema": schema_shortname, "match_schema": match_schema}

    return json.dumps(results)


@api.make()
def api_vault_system_metadata(ctx, coll):
    """Return system metadata of a vault collection.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path to data package

    :returns: Dict system metadata of a vault collection
    """
    space, _, _, _ = pathutil.info(coll)
    if space is not pathutil.Space.VAULT:
        return api.Error('invalid_path', 'Invalid vault path.')

    system_metadata = {}

    # Package size.
    data_count = collection.data_count(ctx, coll)
    collection_count = collection.collection_count(ctx, coll)
    size = collection.size(ctx, coll)
    size_readable = misc.human_readable_size(size)
    system_metadata["Data Package Size"] = "{} files, {} folders, total of {}".format(data_count, collection_count, size_readable)

    # Modified date.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_lastModifiedDateTime'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
        # modified_date = date.fromisoformat(row[0])
        modified_date = parser.parse(row[0])
        modified_date = modified_date.strftime('%Y-%m-%d %H:%M:%S%z')
        system_metadata["Modified date"] = "{}".format(modified_date)

    # Landingpage URL.
    landinpage_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_landingPageUrl'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        landinpage_url = row[0]
        system_metadata["Landingpage"] = "<a href=\"{}\">{}</a>".format(landinpage_url, landinpage_url)

    # Data Package Reference.
    data_package_reference = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.DATA_PACKAGE_REFERENCE),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        data_package_reference = row[0]
        system_metadata["Data Package Reference"] = "<a href=\"yoda/{}\">yoda/{}</a>".format(data_package_reference, data_package_reference)

    # Persistent Identifier EPIC.
    package_epic_pid = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_pid'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        package_epic_pid = row[0]

    package_epic_url = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_epic_url'" % (coll),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        package_epic_url = row[0]

    if package_epic_pid:
        if package_epic_url:
            persistent_identifier_epic = "<a href=\"{}\">{}</a>".format(package_epic_url, package_epic_pid)
        else:
            persistent_identifier_epic = "{}".format(package_epic_pid)
        system_metadata["EPIC Persistent Identifier"] = persistent_identifier_epic

    return system_metadata

# TODO: Case 2
# About system-meta, use _org as system attributes can be derived from a succefully published data package

# TODO: Question, how does irods rule being invoked?
@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_packages_troubleshoot(ctx):
    """Diagnoses if the data package has the expected system AVUs.

    :param ctx: Combined type of a callback and rei struct
    """
    print("Starts rule_batch_vault_packages_troubleshoot2")

    #  Test Example
    coll_name = '/tempZone/home/vault-default-3/research-default-3[1722327809]'
    print("Collection Name:", coll_name)

    # TODO: find out why, how to call api in here
    # system_metadata = api_vault_system_metadata(ctx,coll_name,{} )
    # print("system_metadata",system_metadata)
    # Get the latest metadata of the package
    # metadata_path = meta.get_latest_vault_metadata_path(ctx, coll_name)
    # print("Metadata Path:", metadata_path)

    # Read the metadata from the path
    # metadata = jsonutil.read(ctx, metadata_path)
    # print("Metadata:", metadata)

    # Extract all relevant keys from the metadata, including nested keys
    #def extract_keys(data, prefix=''):
    #    keys = []
    #    if isinstance(data, dict):
    #        for key, value in data.items():
    ##            keys.extend(extract_keys(value, prefix=key))
    #    elif isinstance(data, list):
    #        for item in data:
    #            keys.extend(extract_keys(item, prefix=prefix))
    #    else:
    #        keys.append(prefix.rstrip('.'))
    #    return keys

    #metadata_keys = extract_keys(metadata)
    #print("Metadata Keys:", metadata_keys)

    # Get AVUs of the test package
    avus = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, coll_name)]
    avu_attributes = {avu[0] for avu in avus if avu[0].startswith('org_')}
    print("avu_attributes", avu_attributes)

    #avus = set([
    #    'org_data_package_reference',
    #    'org_vault_status',
    #    'org_license_uri',
    #    'org_action_log'
    #])

    # Define set 'gt_avus' with clear formatting
    gt_avus = set([
        'org_publication_approval_actor',
        'org_publication_randomId',
        'org_license_uri',
        'org_publication_versionDOI',
        'org_publication_dataCiteJsonPath',
        'org_publication_license',
        'org_action_log',
        'org_publication_anonymousAccess',
        'org_publication_versionDOIMinted',
        'org_publication_accessRestriction',
        'org_vault_status',
        'org_publication_landingPagePath',
        'org_data_package_reference',
        'org_publication_licenseUri',
        'org_publication_publicationDate',
        'org_publication_vaultPackage',
        'org_publication_submission_actor',
        'org_publication_status',
        'org_publication_lastModifiedDateTime',
        'org_publication_combiJsonPath',
        'org_publication_landingPageUploaded',
        'org_publication_oaiUploaded',
        'org_publication_landingPageUrl',
        'org_publication_dataCiteMetadataPosted'
    ])

    #groundtruth_coll_name = '/tempZone/home/vault-core-0/research-core-0[1722266819]'
    #gt_avus = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, groundtruth_coll_name)]
    #gt_avu_attributes = {avu[0] for avu in gt_avus if avu[0].startswith('org_')}
    #print("gt_avu_attributes",gt_avu_attributes)

    # Find entries in gt_avus not present in avus
    missing_in_gt = gt_avus - avu_attributes
    # TODO: what if there are entries in avus but not in gt_avus?
    print("missing_in_gt",missing_in_gt)

# TODO: CASE4
# Example:
# /var/www/landingpages/allinone/UU01/JCY2C2.html
# /var/www/moai/metadata/allinone/UU01/JCY2C2.json
# Question: target path? depending on the env? or Vault vs Publication in irods?
# What methods to be used (checksum? but how, MD5? which two files?)

from publication import *



def get_collection_metadata(ctx, coll, prefix):
    """Retrieve all collection metadata.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Collection to retrieve metadata from
    :param prefix: Prefix of the requested metadata

    :return: Dict with all requested (prefixed) attributes and strip off prefix for the key names
    """
    coll_metadata = {}
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME like '" + prefix + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        coll_metadata[row[0][len(prefix):]] = row[1]

    return coll_metadata


def get_publication_state(ctx, vault_package):
    """The publication state is kept as metadata on the vault package.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: Dict with state of the publication process
    """
    publication_state = {
        "status": "Unknown",
        "accessRestriction": "Closed"
    }
    print("inside get_publication_state, the func get_collection_metadata with prefix of org_publication_")
    publ_metadata = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')
    print("and the publication metadata is ",publ_metadata)

    # Take over all actual values as saved earlier.
    for key in publ_metadata:
        publication_state[key] = publ_metadata[key]

    # Handle access restriction.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = '" + vault_package + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        publication_state["accessRestriction"] = row[0]
    print("adding accessRestriction as ",publication_state["accessRestriction"])
    # Handle license.
    license = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%License' AND COLL_NAME = '" + vault_package + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        license = row[0]
    print("adding license as ",license)

    if license != "":
        publication_state["license"] = license
        license_uri = ""
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "META_COLL_ATTR_NAME like '" + constants.UUORGMETADATAPREFIX + "license_uri" + "' AND COLL_NAME = '" + vault_package + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            license_uri = row[0]

        if license_uri != "":
            publication_state["licenseUri"] = license_uri

    publication_state["vaultPackage"] = vault_package
    return publication_state

import datacite
from publication import *

def check_doi_availability(ctx, publication_state, type_flag):
    """Request DOI to check on availability. We want a 404 as return code.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Flag indicating DOI type ('version' or 'base')
    """
    DOI = publication_state[type_flag + "DOI"]

    try:
        httpCode = datacite.metadata_get(ctx, DOI)

        if httpCode == 404:
            publication_state[type_flag + "DOIAvailable"] = "yes"
        elif httpCode in [401, 403, 500, 503, 504]:
            # request failed, worth a retry
            publication_state["status"] = "Retry"
        elif httpCode in [200, 204]:
            # DOI already in use
            publication_state[type_flag + "DOIAvailable"] = "no"
            publication_state["status"] = "Retry"
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "check_doi_availability: timeout received. Will be retried later")
        publication_state["status"] = "Retry"


# TODO: Case3
@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_packages_troubleshoot3(ctx):
    # httpCode = datacite.metadata_get(ctx, DOI)
    vault_package = "/tempZone/home/vault-core-0/research-core-0[1722266819]"
    publication_state = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')
    versionDOI = publication_state["versionDOI"]
    print("versionDOI", versionDOI)
    # TODO: Check is the response not 404 (note the datacite is a remote sever)
    print("metadata_get(ctx, doi)",datacite.metadata_get(ctx, versionDOI))
    # TODO: Create a ticket for the dois typo in metadata_get

import hashlib

def get_md5_of_file(file_path):
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:  # Open the file in binary mode
        for chunk in iter(lambda: f.read(4096), b""):  # Read the file in 4KB chunks
            hash_md5.update(chunk)  # Update the MD5 hash with the chunk
    return hash_md5.hexdigest()  # Return the hexadecimal MD5 hash

import hashlib

def calculate_md5(content):
    """Calculate and return the MD5 checksum for the provided content."""
    # Create an MD5 hash object
    hash_md5 = hashlib.md5()

    # Check if the content is a byte string
    if isinstance(content, bytes):
        # Update the hash object directly with the byte string
        hash_md5.update(content)
    else:
        # Encode and update the hash object with the string
        hash_md5.update(content.encode('utf-8'))

    # Return the hexadecimal MD5 hash
    return hash_md5.hexdigest()

# Example of reading the landing page content
# landingPage = data_object.read(ctx, landingPagePath)
# For demonstration, let's assume landingPage is a string variable already containing data
def calculate_md5_bytes(file_path):
    """Calculate and return the MD5 checksum for the provided file."""
    hash_md5 = hashlib.md5()  # Create a new MD5 hash object
    with open(file_path, 'rb') as f:  # Open the file in binary read mode
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)  # Update the hash with the bytes from the file
    return hash_md5.hexdigest()  # Return the hexadecimal MD5 checksum

import subprocess

def get_remote_md5_ssh(host, username, file_path):
    try:
        # Build the SSH command to execute md5sum remotely using .format()
        ssh_command = "ssh {username}@{host} md5sum -b {file_path}".format(
            username=username, host=host, file_path=file_path
        )

        # Run the command using Popen (for python2 version)
        process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = process.communicate()

        # Check if the command was executed successfully
        if process.returncode == 0:
            # Return only the MD5 hash part
            return stdout.strip().split()[0]
        else:
            print("Error:", stderr)
            return None
    except Exception as e:
        print("An error occurred: {e}".format(e=str(e)))
        return None


from util import data_object, msi
# TODO: Case4
@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_packages_troubleshoot4(ctx):
    """Diagnoses landing page file and combi json

    :param ctx: Combined type of a callback and rei struct
    """
    # Example landing page (only for published data package)
    # TODO: Filter with only published packaged
    vault_package = "/tempZone/home/vault-core-0/research-core-0[1722266819]"
    publication_state = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')

    #publication_state = get_collection_metadata(ctx, vault_package)

    #publication_state = get_publication_state(ctx, vault_package)
    print("publication_state",publication_state)
    landingPagePath = publication_state["landingPagePath"]
    dataCiteJsonPath = publication_state["dataCiteJsonPath"]
    print("landingPagePath",landingPagePath)
    print("dataCiteJsonPath",dataCiteJsonPath)

    landingPageUrl = publication_state["landingPageUrl"]

    print("landingPageUrl",landingPageUrl)

    #md5_result = get_md5_of_file(landingPagePath)
    #print("MD5 Checksum:", md5_result)
    iter = genquery.row_iterator(
        "ORDER(DATA_NAME), DATA_SIZE, DATA_CHECKSUM",
        "COLL_NAME = '{}'".format(vault_package),
        genquery.AS_LIST, ctx
    )
    checksums = [{"name": row[0], "size": misc.human_readable_size(int(row[1])), "checksum": data_object.decode_checksum(row[2])} for row in iter]
    print("checksums of collection",checksums)

    # TODO: how to read a file
    with open("/var/lib/irods/Vault1_2/yoda/publication/JCY2C2.html", 'rb') as f:
        pass
    checksum_inbox = calculate_md5_bytes("/var/lib/irods/Vault1_2/yoda/publication/JCY2C2.html")
    print("checksum_inbox",checksum_inbox)
    # Use dataobject.read FIXME: Size arg is not added yet
    landingPage = data_object.read(ctx, landingPagePath)
    print("landingPage",landingPage)
    md5_landingPage = calculate_md5(landingPage)
    print("md5 landingPage in irods",md5_landingPage)
    # 34e107a24f9fb826a4c3f6f6956d3aaf
    # binary mode checksum 0d387c96abec5ad84b08ffeedf247e99
    # TODO: how to read a file from public server
    # use ssh md5 linux cmd
    host = "combined.yoda.test"
    username = "inbox"
    file_path = "/var/www/landingpages/allinone/UU01/JCY2C2.html"
    md5_hash = get_remote_md5_ssh(host, username, file_path)
    print("MD5 Hash:", md5_hash)
    # or use requests.get such as metadata_get which is unlikely actually
    #with open(vault_package, "rb") as f:  # Open the file in binary mode?
    #    pass
    # FIXME: datacite json url (public server)

    # get md5/checksum of the landing page
    # get md5 of the same landing page in datacite server

    # print them out

@rule.make(inputs=[], outputs=[0])
def rule_batch_find_published_data_packages(ctx):
    '''Find data packages with AVUs including org_vault_status = "Published" '''
    # Find all vault collections
    user_zone = user.zone(ctx)

   # Query condition to fetch data
    query_condition = (
        "COLL_NAME like '/{}/home/vault-%%' AND META_COLL_ATTR_NAME like 'org_vault_status' AND META_COLL_ATTR_VALUE like 'PUBLISHED'".format(user_zone)
    )
    # Attributes to fetch
    query_attributes = "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS"
    print("query_condition",query_condition)
    print("find all published data packages")
    try:
        iter = genquery.row_iterator(query_attributes, query_condition, genquery.AS_LIST, ctx)
        print("after genquery")

        # Print each row
        for row in iter:
            print(row[0],row[1],row[2],row[3])
            #print("Collection Name: {}, Attribute Name: {}, Attribute Value: {}, Attribute Units: {}".format(*row))
    except Exception as e:
        print("An error occurred while executing the query:", e)
