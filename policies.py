# -*- coding: utf-8 -*-
"""iRODS policy implementations."""

__copyright__ = 'Copyright (c) 2020-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

import session_vars

import datarequest
import folder
import policies_datapackage_status
import policies_datarequest_status
import policies_folder_status
import policies_intake
import replication
import revisions
import vault
from util import *


# Policy check functions {{{

# These can be called from anywhere to check the authorization for a certain
# operation. A check function, prefixed with 'can_', will always return either
# policy.succeed() or policy.fail(). If the result is policy.fail(), the reason
# for the failure can be obtained in the 'reason' property of the result object.
# This can be used for reporting authorization failures to clients.

# Authorize I/O operations {{{

# Separate from ACLs, we deny certain operations on collections and data in
# research or deposit folders when paths are locked.

def can_coll_create(ctx, actor, coll):
    """Disallow creating collections in locked folders."""
    log.debug(ctx, 'check coll create <{}>'.format(coll))

    if pathutil.info(coll).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        if folder.is_locked(ctx, pathutil.dirname(coll)) and not user.is_admin(ctx, actor):
            return policy.fail('Parent folder is locked')

    if pathutil.info(coll).space is pathutil.Space.INTAKE:
        if policies_intake.is_coll_in_locked_dataset(ctx, user.user_and_zone(ctx), pathutil.chop(coll)[0]):
            return policy.fail('Collection part of a locked dataset')

    return policy.succeed()


def can_coll_delete(ctx, actor, coll):
    """Disallow deleting collections in locked folders and collections containing locked folders."""
    log.debug(ctx, 'check coll delete <{}>'.format(coll))

    if re.match(r'^/[^/]+/home/[^/]+$', coll) and not user.is_admin(ctx, actor):
        return policy.fail('Cannot delete or move collections directly under /home')

    if pathutil.info(coll).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        if not user.is_admin(ctx, actor) and folder.has_locks(ctx, coll):
            return policy.fail('Folder or subfolder is locked')

    if pathutil.info(coll).space is pathutil.Space.INTAKE:
        if policies_intake.coll_in_path_of_locked_dataset(ctx, user.user_and_zone(ctx), coll):
            return policy.fail('Collection part of a locked dataset')

    return policy.succeed()


def can_coll_move(ctx, actor, src, dst):
    log.debug(ctx, 'check coll move <{}> -> <{}>'.format(src, dst))

    return policy.all(can_coll_delete(ctx, actor, src),
                      can_coll_create(ctx, actor, dst))


def can_data_create(ctx, actor, path):
    log.debug(ctx, 'check data create <{}>'.format(path))

    if pathutil.info(path).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        if folder.is_locked(ctx, pathutil.dirname(path)):
            # Parent coll locked?
            if not user.is_admin(ctx, actor):
                return policy.fail('Folder is locked')
        elif folder.is_data_locked(ctx, path):
            # If the parent coll is not locked, there might still be a lock on
            # an existing destination data object (though this situation cannot
            # arise through portal actions).
            if not user.is_admin(ctx, actor):
                return policy.fail('Destination is locked')

    if pathutil.info(path).space is pathutil.Space.INTAKE:
        if policies_intake.is_data_in_locked_dataset(ctx, user.user_and_zone(ctx), path):
            return policy.fail('Data part of a locked dataset')

    return policy.succeed()


def can_data_write(ctx, actor, path):
    log.debug(ctx, 'check data write <{}>'.format(path))

    # Disallow writing to locked objects in research and deposit folders.
    if pathutil.info(path).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        if folder.is_data_locked(ctx, path) and not user.is_admin(ctx, actor):
            return policy.fail('Data object is locked')

    # Disallow writing to locked datasets in intake.
    if pathutil.info(path).space is pathutil.Space.INTAKE:
        if policies_intake.is_data_in_locked_dataset(ctx, user.user_and_zone(ctx), path):
            return policy.fail('Data part of a locked dataset')

    return policy.succeed()


def can_data_delete(ctx, actor, path):
    if re.match(r'^/[^/]+/home/[^/]+$', path) and not user.is_admin(ctx, actor):
        return policy.fail('Cannot delete or move data directly under /home')

    if pathutil.info(path).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        if not user.is_admin(ctx, actor) and folder.is_data_locked(ctx, path):
            return policy.fail('Folder is locked')

    if pathutil.info(path).space is pathutil.Space.INTAKE:
        if policies_intake.is_data_in_locked_dataset(ctx, user.user_and_zone(ctx), path):
            return policy.fail('Data part of a locked dataset')

    return policy.succeed()


def can_data_copy(ctx, actor, src, dst):
    log.debug(ctx, 'check data copy <{}> -> <{}>'.format(src, dst))
    return can_data_create(ctx, actor, dst)


def can_data_move(ctx, actor, src, dst):
    log.debug(ctx, 'check data move <{}> -> <{}>'.format(src, dst))
    return policy.all(can_data_delete(ctx, actor, src),
                      can_data_create(ctx, actor, dst))


# }}}
# Hooking pre peps to the above check functions {{{

# Ideally we would use only dynamic PEPs, as they are more consistent and
# appear to be the preferred (by iRODS) way of implementing policies.
# However dynamic API PEPs, in contrast with their apparently equivalent
# static PEPs, are not triggered by MSIs and therefore cannot be relied upon.
# So we again fall back to static PEPs, and add only a few dynamic PEPs where
# they provide benefits that the static PEPs cannot provide.
#
# The actual static PEPs are currently in the rule language part of the ruleset.
# Most of them 'cut' and call identically named Python functions in this file.

@policy.require()
def py_acPreprocForCollCreate(ctx):
    log.debug(ctx, 'py_acPreprocForCollCreate')
    # print(jsonutil.dump(session_vars.get_map(ctx.rei)))
    return can_coll_create(ctx, user.user_and_zone(ctx),
                           str(session_vars.get_map(ctx.rei)['collection']['name']))


@policy.require()
def py_acPreprocForRmColl(ctx):
    log.debug(ctx, 'py_acPreprocForRmColl')
    # print(jsonutil.dump(session_vars.get_map(ctx.rei)))
    return can_coll_delete(ctx, user.user_and_zone(ctx),
                           str(session_vars.get_map(ctx.rei)['collection']['name']))


@policy.require()
def py_acPreprocForDataObjOpen(ctx):
    log.debug(ctx, 'py_acPreprocForDataObjOpen')
    # data object reads are always allowed.
    # writes are blocked e.g. when the object is locked (unless actor is a rodsadmin).
    if session_vars.get_map(ctx.rei)['data_object']['write_flag'] == 1:
        return can_data_write(ctx, user.user_and_zone(ctx),
                              str(session_vars.get_map(ctx.rei)['data_object']['object_path']))
    else:
        return policy.succeed()


@policy.require()
def py_acDataDeletePolicy(ctx):
    log.debug(ctx, 'py_acDataDeletePolicy')
    return (policy.succeed()
            if can_data_delete(ctx, user.user_and_zone(ctx),
                               str(session_vars.get_map(ctx.rei)['data_object']['object_path']))
            else ctx.msiDeleteDisallowed())


@policy.require()
def py_acPreProcForObjRename(ctx, src, dst):
    log.debug(ctx, 'py_acPreProcForObjRename')

    # irods/lib/api/include/dataObjInpOut.h
    RENAME_DATA_OBJ = 11
    RENAME_COLL     = 12

    if session_vars.get_map(ctx.rei)['operation_type'] == RENAME_DATA_OBJ:
        return can_data_move(ctx, user.user_and_zone(ctx), src, dst)
    elif session_vars.get_map(ctx.rei)['operation_type'] == RENAME_COLL:
        return can_coll_move(ctx, user.user_and_zone(ctx), src, dst)

    # if ($objPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".[^/]*/.*") {


@policy.require()
def py_acPostProcForPut(ctx):
    log.debug(ctx, 'py_acPostProcForPut')
    # Data object creation cannot be prevented by API dynpeps and static PEPs,
    # due to how MSIs work. Thus, this ugly workaround specifically for MSIs.
    path = str(session_vars.get_map(ctx.rei)['data_object']['object_path'])
    x = can_data_create(ctx, user.user_and_zone(ctx), path)

    if not x:
        data_object.remove(ctx, path, force=True)

    return x


@policy.require()
def py_acPostProcForCopy(ctx):
    # See py_acPostProcForPut.
    log.debug(ctx, 'py_acPostProcForCopy')

    path = str(session_vars.get_map(ctx.rei)['data_object']['object_path'])
    x = can_data_create(ctx, user.user_and_zone(ctx), path)

    if not x:
        data_object.remove(ctx, path, force=True)

    return x


# Disabled: caught by acPreprocForCollCreate
# @policy.require()
# def pep_api_coll_create_pre(ctx, instance_name, rs_comm, coll_create_inp):
#     log.debug(ctx, 'pep_api_coll_create_pre')
#     return can_coll_create(ctx, user.user_and_zone(ctx),
#                            str(coll_create_inp.collName))

# Disabled: caught by acPreprocForRmColl
# @policy.require()
# def pep_api_rm_coll_pre(ctx, instance_name, rs_comm, rm_coll_inp, coll_opr_stat):
#     log.debug(ctx, 'pep_api_rm_coll_pre')
#     return can_coll_delete(ctx, user.user_and_zone(ctx),
#                            str(rm_coll_inp.collName))

# Disabled: caught by acPostProcForPut
# @policy.require()
# def pep_api_data_obj_put_pre(ctx, instance_name, rs_comm, data_obj_inp, data_obj_inp_bbuf, portal_opr_out):
#     # Matches data object creation/overwrite via iput.
#     log.debug(ctx, 'pep_api_data_obj_put_pre')
#     return can_data_create(ctx, user.user_and_zone(ctx),
#                            str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_create_pre(ctx, instance_name, rs_comm, data_obj_inp):
    log.debug(ctx, 'pep_api_data_obj_create_pre')

    # Catch object creation/overwrite via Davrods and PRC.
    # This should also catch object creation by any other client that isn't so
    # nice as to set the "PUT_OPR" flag, and thereby bypasses the static PUT postproc above.
    # Note that this should only be needed for create actions, not open in general:
    # for overwriting there is still a PRE static PEP that applies - acPreprocForDataObjOpen.
    return can_data_create(ctx, user.user_and_zone(ctx),
                           str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_create_and_stat_pre(ctx, instance_name, rs_comm, data_obj_inp, open_stat):
    log.debug(ctx, 'pep_api_data_obj_create_and_stat_pre')

    # Not triggered by any of our clients currently, but needed for completeness.
    return can_data_create(ctx, user.user_and_zone(ctx),
                           str(data_obj_inp.objPath))


# Disabled: caught by acPostProcForCopy
# @policy.require()
# def pep_api_data_obj_copy_pre(ctx, instance_name, rs_comm, data_obj_copy_inp, trans_stat):
#     log.debug(ctx, 'pep_api_data_obj_copy_pre')
#     return can_data_create(ctx, user.user_and_zone(ctx),
#                            str(data_obj_copy_inp.destDataObjInp.objPath))

# Disabled: caught by acPreProcForObjRename
# @policy.require()
# def pep_api_data_obj_rename_pre(ctx, instance_name, rs_comm, data_obj_rename_inp):
#     log.debug(ctx, 'pep_api_data_obj_rename_pre')

#     # API name says data_obj, but it applies to both data and collections
#     # depending on 'oprType'.

#     # irods/lib/api/include/dataObjInpOut.h
#     RENAME_DATA_OBJ = 11
#     RENAME_COLL     = 12

#     if data_obj_rename_inp.srcDataObjInp.oprType == RENAME_DATA_OBJ:
#         return can_data_move(ctx, user.user_and_zone(ctx),
#                              str(data_obj_rename_inp.srcDataObjInp.objPath),
#                              str(data_obj_rename_inp.destDataObjInp.objPath))
#     elif data_obj_rename_inp.srcDataObjInp.oprType == RENAME_COLL:
#         return can_coll_move(ctx, user.user_and_zone(ctx),
#                              str(data_obj_rename_inp.srcDataObjInp.objPath),
#                              str(data_obj_rename_inp.destDataObjInp.objPath))


@policy.require()
def pep_api_data_obj_trim_pre(ctx, instance_name, rs_comm, data_obj_inp):
    log.debug(ctx, 'pep_api_data_obj_trim_pre')
    return can_data_write(ctx, user.user_and_zone(ctx),
                          str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_truncate_pre(ctx, instance_name, rs_comm, data_obj_truncate_inp):
    log.debug(ctx, 'pep_api_data_obj_truncate_pre')
    return can_data_write(ctx, user.user_and_zone(ctx),
                          str(data_obj_truncate_inp.objPath))

# Disabled: caught by acDataDeletePolicy
# @policy.require()
# def pep_api_data_obj_unlink_pre(ctx, instance_name, rs_comm, data_obj_unlink_inp):
#     log.debug(ctx, 'pep_api_data_obj_unlink_pre')
#     return can_data_delete(ctx, user.user_and_zone(ctx),
#                            str(data_obj_unlink_inp.objPath))

# }}}
# Authorize metadata operations {{{

# Disabled: caught by py_acPreProcForModifyAVUMetadata
# @policy.require()
# def pep_api_mod_avu_metadata_pre(ctx, instance_name, rs_comm, mod_avumetadata_inp):
#     log.debug(ctx, 'pep_api_mod_avu_metadata_pre')
#     return can_meta_modify(ctx, actor, AvuOpr(mod_avumetadata_inp))


# Policy for most AVU changes
@policy.require()
def py_acPreProcForModifyAVUMetadata(ctx, option, obj_type, obj_name, attr, value, unit):

    actor = user.user_and_zone(ctx)

    if obj_type not in ['-d', '-C']:
        # Metadata policies below only apply to collections.
        return policy.succeed()

    space = pathutil.info(obj_name).space

    if space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT] and attr == constants.IISTATUSATTRNAME:
        # Research or deposit folder status change. Validate.
        if not unit == '':
            return policy.fail('Invalid status attribute')
        if option not in ['set', 'rm', 'rmw']:
            # "add" has no meaning on the status attribute, as there must
            # always be either 0 or 1 instance of this attr.
            return policy.fail('Only "set" and "rm" operations allowed on folder status attribute')

        if option in ['rm', 'rmw']:
            option, value = 'set', ''

        x = policies_folder_status.can_set_folder_status_attr(ctx, actor, obj_name, value)
        if not x:
            return x

        return policies_folder_status.pre_status_transition(ctx, obj_name, x[0], x[1])

    elif (space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]
          and attr in [constants.UUORGMETADATAPREFIX + "revision_scheduled",
                       constants.UUORGMETADATAPREFIX + "replication_scheduled"]):
        # Research or deposit organizational metadata.
        if user.is_admin(ctx, actor):
            return policy.succeed()

        if option in ['add']:
            return policy.succeed()
        else:
            return policy.fail('Only "add" operations allowed on attribute')

    elif space is pathutil.Space.VAULT and attr == constants.IIVAULTSTATUSATTRNAME:
        if not user.is_admin(ctx, actor):
            return policy.fail('No permission to change vault status')

        x = policies_datapackage_status.can_set_datapackage_status_attr(ctx, actor, obj_name, value)
        if not x:
            return x

        return policies_datapackage_status.pre_status_transition(ctx, obj_name, x[0], x[1])

    elif obj_type == '-C' and space is pathutil.Space.RESEARCH and unit.startswith(constants.UUUSERMETADATAROOT + '_'):
        # Research package metadata, set when saving the metadata form.
        # Allow if object is not locked.

        if (not folder.is_locked(ctx, obj_name)) or user.is_admin(ctx, actor):
            return policy.succeed()
        else:
            return policy.fail('Folder is locked')

    elif space is pathutil.Space.DATAREQUEST and attr == datarequest.DATAREQUESTSTATUSATTRNAME:
        # Check if user is permitted to change the status
        if not user.is_admin(ctx, actor):
            return policy.fail('No permission to change datarequest status')

        # Datarequest status change. Validate.
        return policies_datarequest_status.can_set_datarequest_status(ctx, obj_name, value)

    else:
        # Allow metadata operations in general if they do not affect reserved
        # attributes.
        return policy.succeed()


# imeta mod
@policy.require()
def py_acPreProcForModifyAVUMetadata_mod(ctx, *args):
    actor = user.user_and_zone(ctx)
    if user.is_admin(ctx, actor):
        return policy.succeed()

    if t_dst not in ['-d', '-C']:
        return policy.succeed()

    if pathutil.info(dst).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT, pathutil.Space.VAULT]:
        return policy.fail('Metadata mod not allowed')


# imeta cp
@policy.require()
def py_acPreProcForModifyAVUMetadata_cp(ctx, _, t_src, t_dst, src, dst):
    actor = user.user_and_zone(ctx)
    if user.is_admin(ctx, actor):
        return policy.succeed()

    if t_dst not in ['-d', '-C']:
        return policy.succeed()

    if pathutil.info(dst).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT, pathutil.Space.VAULT]:
        # Prevent imeta cp. Previously this was blocked by a buggy policy.
        # We now block this explicitly in research & vault because the action is
        # too difficult to reliably validate w.r.t. for example folder status transitions,
        # and no rules make use of this code path.
        return policy.fail('Metadata copy not allowed')

    return policy.succeed()


# This PEP is called after a AVU is added (option = 'add'), set (option =
# 'set') or removed (option = 'rm') in the research area or the vault. Post
# conditions defined in folder.py and iiVaultTransitions.r
# are called here.
@rule.make()
def py_acPostProcForModifyAVUMetadata(ctx, option, obj_type, obj_name, attr, value, unit):
    info = pathutil.info(obj_name)

    if attr == constants.IISTATUSATTRNAME and info.space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        status = constants.research_package_state.FOLDER.value if option in ['rm', 'rmw'] else value
        policies_folder_status.post_status_transition(ctx, obj_name, str(user.user_and_zone(ctx)), status)

    elif info.space is pathutil.Space.VAULT:
        if attr == constants.IIVAULTSTATUSATTRNAME:
            policies_datapackage_status.post_status_transition(ctx, obj_name, str(user.user_and_zone(ctx)), value)
        elif attr.startswith(constants.UUORGMETADATAPREFIX) and attr != constants.IIARCHIVEATTRNAME:
            vault.update_archive(ctx, obj_name, attr)

    # Send emails after datarequest status transition if appropriate
    elif attr == datarequest.DATAREQUESTSTATUSATTRNAME and info.space is pathutil.Space.DATAREQUEST:
        policies_datarequest_status.post_status_transition(ctx, obj_name, value)
# }}}


# Authorize access control operations {{{

# ichmod
@policy.require()
def pep_api_mod_access_control_pre(ctx, instance_name, rs_comm, mod_access_control_inp):
    log.debug(ctx, 'pep_api_mod_access_control_pre')
    actor = user.user_and_zone(ctx)
    if user.is_admin(ctx, actor):
        return policy.succeed()

    path = str(mod_access_control_inp.path)
    if pathutil.info(path).space in [pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT]:
        # Prevent ichmod in research and deposit space by normal users.
        return policy.fail('Mod access control not allowed')

    return policy.succeed()

# }}}


# ExecCmd {{{
@policy.require()
def py_acPreProcForExecCmd(ctx, cmd, args, addr, hint):
    actor = user.user_and_zone(ctx)

    # No restrictions for rodsadmin and priv group.
    if user.is_admin(ctx, actor):
        return policy.succeed()

    if config.enable_tape_archive and cmd in ['dmattr', 'dmget', 'admin-tape-archive-set-state.sh']:
        return policy.succeed()

    if user.is_member_of(ctx, 'priv-execcmd-all', actor):
        return policy.succeed()

    if not (hint == addr == ''):
        return policy.fail('Disallowed hint/addr in execcmd')

    # allow 'admin-*' scripts, if first arg is the actor username&zone.
    if cmd.startswith('admin-'):
        if args == str(actor) or args.startswith(str(actor) + ' '):
            return policy.succeed()
        else:
            return policy.fail('Actor not given as first arg to admin- execcmd')

    # Allow scheduled scripts.
    if cmd.startswith('scheduled-'):
        return policy.succeed()

    return policy.fail('No execcmd privileges for this command')


# Internal function to determine whether changes to data objects on a particular
# resource need to trigger policies (e.g. asynchronous replication) by default.
def resource_should_trigger_policies(resource):
    if resource in config.resource_primary:
        return True

    if resource in config.resource_vault:
        return True

    for pattern in config.resource_trigger_pol:
        if re.match(pattern, resource):
            return True

    return False


@rule.make()
def pep_resource_modified_post(ctx, instance_name, _ctx, out):
    if not resource_should_trigger_policies(instance_name):
        return

    path = _ctx.map()['logical_path']
    zone = _ctx.map()['user_rods_zone']
    username = _ctx.map()['user_user_name']
    info = pathutil.info(path)

    for resource in config.resource_replica:
        replication.replicate_asynchronously(ctx, path, instance_name, resource)

    if config.enable_tape_archive:
        ctx.uuTapeArchiveReplicateAsynchronously(path)

    try:
        # Import metadata if a metadata JSON file was changed.
        # Example matches:
        # "/tempZone/home/research-any/possible/path/to/yoda-metadata.json"
        # "/tempZone/home/deposit-any/deposit[123]/yoda-metadata.json"
        # "/tempZone/home/vault-any/possible/path/to/yoda-metadata[123][1].json"
        # "/tempZone/home/datamanager-category/vault-path/to/yoda-metadata.json"
        if ((info.space in (pathutil.Space.RESEARCH, pathutil.Space.DEPOSIT, pathutil.Space.DATAMANAGER)
                and pathutil.basename(info.subpath) == constants.IIJSONMETADATA)
            or (info.space is pathutil.Space.VAULT
                # Vault jsons have a [timestamp] in the file name.
                and re.match(r'{}\[[^/]+\]\.{}$'.format(*map(re.escape, pathutil.chopext(constants.IIJSONMETADATA))),
                             pathutil.basename(info.subpath)))):
            # Path is a metadata file, ingest.
            log.write(ctx, 'metadata JSON <{}> modified by {}, ingesting'.format(path, username))
            ctx.rule_meta_modified_post(path, username, zone)
        elif (info.space is pathutil.Space.DATAREQUEST
              and pathutil.basename(info.subpath) == datarequest.DATAREQUEST + datarequest.JSON_EXT):
            request_id = pathutil.dirname(info.subpath)
            log.write(ctx, 'datarequest JSON <{}> modified by {}, ingesting'.format(path, username))
            datarequest.datarequest_sync_avus(ctx, request_id)

    except Exception as e:
        # The rules on metadata are run synchronously and could fail.
        # Log errors, but continue with revisions.
        log.write(ctx, 'rule_meta_modified_post failed: ' + str(e))

    # ctx.uuResourceModifiedPostRevision(instance_name, zone, path)
    revisions.resource_modified_post_revision(ctx, instance_name, zone, path)


@rule.make()
def py_acPostProcForObjRename(ctx, src, dst):
    # Update ACLs to give correct group ownership when an object is moved into
    # a different research- or grp- collection.
    info = pathutil.info(dst)
    if info.space is pathutil.Space.RESEARCH or info.group.startswith(constants.IIGRPPREFIX):
        if len(info.subpath) and info.group != pathutil.info(src).group:
            ctx.uuEnforceGroupAcl(dst)


@rule.make(inputs=[0, 1, 2, 3, 4, 5, 6], outputs=[2])
def pep_resource_resolve_hierarchy_pre(ctx, resource, _ctx, out, operation, host, parser, vote):
    if not config.arb_enabled or operation != "CREATE":
        return

    arb_data = arb_data_manager.ARBDataManager()
    arb_status = arb_data.get(ctx, resource)

    if arb_status == constants.arb_status.FULL:
        return "read=1.0;write=0.0"
    else:
        return "read=1.0;write=1.0"


@rule.make(inputs=[0], outputs=[1])
def rule_check_anonymous_access_allowed(ctx, address):
    """Check if access to the anonymous account is allowed from a particular network
       address. Non-local access to the anonymous account should only be allowed from
       DavRODS servers, for security reasons.

    :param ctx:  Combined type of a callback and rei struct
    :param address: Network address to check

    :returns: 'true' if access from this network address is allowed; otherwise 'false'
    """
    permit_list = ["127.0.0.1"] + config.remote_anonymous_access
    return "true" if address in permit_list else "false"

# }}}
# }}}
