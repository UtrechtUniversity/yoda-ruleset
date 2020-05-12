# -*- coding: utf-8 -*-
"""iRODS policy implementations"""

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

import re
import folder
import vault
import policies_folder_status
import session_vars


# Policy check functions {{{

# These can be called from anywhere to check the authorization for a certain
# operation. A check function, prefixed with 'can_', will always return either
# policy.succeed() or policy.fail(). If the result is policy.fail(), the reason
# for the failure can be obtained in the 'reason' property of the result object.
# This can be used for reporting authorization failures to clients.

# Authorize I/O operations {{{

# Separate from ACLs, we deny certain operations on collections and data in
# research folders when paths are locked.

def can_coll_create(ctx, actor, coll):
    """Disallow creating collections in locked folders"""
    log.debug(ctx, 'check coll create <{}>'.format(coll))

    if pathutil.info(coll).space is not pathutil.Space.RESEARCH:
        # Lock policy only holds for research folders.
        return policy.succeed()

    if folder.is_locked(ctx, pathutil.dirname(coll)) and not user.is_admin(ctx, actor):
        return policy.fail('Parent folder is locked')

    return policy.succeed()


def can_coll_delete(ctx, actor, coll):
    """Disallow deleting collections in locked folders and collections containing locked folders."""
    log.debug(ctx, 'check coll delete <{}>'.format(coll))

    if re.match(r'^/[^/]+/home/[^/]+$', coll) and not user.is_admin(ctx, actor):
        return policy.fail('Cannot delete or move collections directly under /home')

    if pathutil.info(coll).space is pathutil.Space.RESEARCH:
        if folder.has_locks(ctx, coll) and not user.is_admin(ctx, actor):
            return policy.fail('Folder or subfolder is locked')

    return policy.succeed()


def can_coll_move(ctx, actor, src, dst):
    log.debug(ctx, 'check coll move <{}> -> <{}>'.format(src, dst))

    return policy.all(can_coll_delete(ctx, actor, src),
                      can_coll_create(ctx, actor, dst))


def can_data_create(ctx, actor, path):
    log.debug(ctx, 'check data create <{}>'.format(path))

    if pathutil.info(path).space is pathutil.Space.RESEARCH:
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

    return policy.succeed()


def can_data_write(ctx, actor, path):
    log.debug(ctx, 'check data write <{}>'.format(path))

    # Disallow writing to locked objects in research folders.
    if pathutil.info(path).space is pathutil.Space.RESEARCH:
        if folder.is_data_locked(ctx, path) and not user.is_admin(ctx, actor):
            return policy.fail('Data object is locked')

    return policy.succeed()


def can_data_delete(ctx, actor, path):

    if re.match(r'^/[^/]+/home/[^/]+$', path) and not user.is_admin(ctx, actor):
        return policy.fail('Cannot delete or move data directly under /home')

    if pathutil.info(path).space is pathutil.Space.RESEARCH:
        if folder.is_data_locked(ctx, path) and not user.is_admin(ctx, actor):
            return policy.fail('Folder is locked')

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
# However dynamic API PEPs, in contrast with their appearantly equivalent
# static PEPs, are not triggered by MSIs and therefore cannot be relied upon.
# So we again fall back to static PEPs, and add only a few dynamic PEPs where
# they provide benefits that the static PEPs cannot provide.
#
# The actual static PEPs are currenly in the rule language part of the ruleset.
# Most of them 'cut' and call identically named Python functions in this file.

@policy.require()
def py_acPreprocForCollCreate(ctx):
    log._debug(ctx, 'py_acPreprocForCollCreate')
    # print(jsonutil.dump(session_vars.get_map(ctx.rei)))
    return can_coll_create(ctx, user.user_and_zone(ctx),
                           str(session_vars.get_map(ctx.rei)['collection']['name']))


@policy.require()
def py_acPreprocForRmColl(ctx):
    log._debug(ctx, 'py_acPreprocForRmColl')
    # print(jsonutil.dump(session_vars.get_map(ctx.rei)))
    return can_coll_delete(ctx, user.user_and_zone(ctx),
                           str(session_vars.get_map(ctx.rei)['collection']['name']))


@policy.require()
def py_acPreprocForDataObjOpen(ctx):
    log._debug(ctx, 'py_acPreprocForDataObjOpen')
    # data object reads are always allowed.
    # writes are blocked e.g. when the object is locked (unless actor is a rodsadmin).
    if session_vars.get_map(ctx.rei)['data_object']['write_flag'] == 1:
        return can_data_write(ctx, user.user_and_zone(ctx),
                              str(session_vars.get_map(ctx.rei)['data_object']['object_path']))
    else:
        return policy.succeed()


@policy.require()
def py_acDataDeletePolicy(ctx):
    log._debug(ctx, 'py_acDataDeletePolicy')
    return (policy.succeed()
            if can_data_delete(ctx, user.user_and_zone(ctx),
                               str(session_vars.get_map(ctx.rei)['data_object']['object_path']))
            else ctx.msiDeleteDisallowed())


@policy.require()
def py_acPreProcForObjRename(ctx, src, dst):
    log._debug(ctx, 'py_acPreProcForObjRename')

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
    log._debug(ctx, 'py_acPostProcForPut')
    # Data object creation cannot be prevented by API dynpeps and static PEPs,
    # due to how MSIs work. Thus, this ugly workaround specifically for MSIs.
    path = str(session_vars.get_map(ctx.rei)['data_object']['object_path'])
    x = can_data_create(ctx, user.user_and_zone(ctx), path)

    if not x:
        data_object.remove(ctx, path)

    return x


@policy.require()
def py_acPostProcForCopy(ctx):
    # See py_acPostProcForPut.
    log._debug(ctx, 'py_acPostProcForCopy')

    path = str(session_vars.get_map(ctx.rei)['data_object']['object_path'])
    x = can_data_create(ctx, user.user_and_zone(ctx), path)

    if not x:
        data_object.remove(ctx, path)

    return x


# Disabled: caught by acPreprocForCollCreate
# @policy.require()
# def pep_api_coll_create_pre(ctx, instance_name, rs_comm, coll_create_inp):
#     log._debug(ctx, 'pep_api_coll_create_pre')
#     return can_coll_create(ctx, user.user_and_zone(ctx),
#                            str(coll_create_inp.collName))

# Disabled: caught by acPreprocForRmColl
# @policy.require()
# def pep_api_rm_coll_pre(ctx, instance_name, rs_comm, rm_coll_inp, coll_opr_stat):
#     log._debug(ctx, 'pep_api_rm_coll_pre')
#     return can_coll_delete(ctx, user.user_and_zone(ctx),
#                            str(rm_coll_inp.collName))

# Disabled: caught by acPostProcForPut
# @policy.require()
# def pep_api_data_obj_put_pre(ctx, instance_name, rs_comm, data_obj_inp, data_obj_inp_bbuf, portal_opr_out):
#     # Matches data object creation/overwrite via iput.
#     log._debug(ctx, 'pep_api_data_obj_put_pre')
#     return can_data_create(ctx, user.user_and_zone(ctx),
#                            str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_create_pre(ctx, instance_name, rs_comm, data_obj_inp):
    log._debug(ctx, 'pep_api_data_obj_create_pre')

    # Catch object creation/overwrite via Davrods and PRC.
    # This should also catch object creation by any other client that isn't so
    # nice as to set the "PUT_OPR" flag, and thereby bypasses the static PUT postproc above.
    # Note that this should only be needed for create actions, not open in general:
    # for overwriting there is still a PRE static PEP that applies - acPreprocForDataObjOpen.
    return can_data_create(ctx, user.user_and_zone(ctx),
                           str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_create_and_stat_pre(ctx, instance_name, rs_comm, data_obj_inp, open_stat):
    log._debug(ctx, 'pep_api_data_obj_create_and_stat_pre')

    # Not triggered by any of our clients currently, but needed for completeness.
    return can_data_create(ctx, user.user_and_zone(ctx),
                           str(data_obj_inp.objPath))


# Disabled: caught by acPostProcForCopy
# @policy.require()
# def pep_api_data_obj_copy_pre(ctx, instance_name, rs_comm, data_obj_copy_inp, trans_stat):
#     log._debug(ctx, 'pep_api_data_obj_copy_pre')
#     return can_data_create(ctx, user.user_and_zone(ctx),
#                            str(data_obj_copy_inp.destDataObjInp.objPath))

# Disabled: caught by acPreProcForObjRename
# @policy.require()
# def pep_api_data_obj_rename_pre(ctx, instance_name, rs_comm, data_obj_rename_inp):
#     log._debug(ctx, 'pep_api_data_obj_rename_pre')

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
    log._debug(ctx, 'pep_api_data_obj_trim_pre')
    return can_data_write(ctx, user.user_and_zone(ctx),
                          str(data_obj_inp.objPath))


@policy.require()
def pep_api_data_obj_truncate_pre(ctx, instance_name, rs_comm, data_obj_truncate_inp):
    log._debug(ctx, 'pep_api_data_obj_truncate_pre')
    return can_data_write(ctx, user.user_and_zone(ctx),
                          str(data_obj_inp.objPath))

# Disabled: caught by acDataDeletePolicy
# @policy.require()
# def pep_api_data_obj_unlink_pre(ctx, instance_name, rs_comm, data_obj_unlink_inp):
#     log._debug(ctx, 'pep_api_data_obj_unlink_pre')
#     return can_data_delete(ctx, user.user_and_zone(ctx),
#                            str(data_obj_unlink_inp.objPath))

# }}}
# Authorize metadata operations {{{

# Disabled: caught by py_acPreProcForModifyAVUMetadata
# @policy.require()
# def pep_api_mod_avu_metadata_pre(ctx, instance_name, rs_comm, mod_avumetadata_inp):
#     log._debug(ctx, 'pep_api_mod_avu_metadata_pre')
#     return can_meta_modify(ctx, actor, AvuOpr(mod_avumetadata_inp))


# Policy for most AVU changes
@policy.require()
def py_acPreProcForModifyAVUMetadata(ctx, option, obj_type, obj_name, attr, value, unit):

    actor = user.user_and_zone(ctx)

    if obj_type not in ['-d', '-C']:
        # Metadata policies below only apply to collections.
        return policy.succeed()

    space = pathutil.info(obj_name).space

    if space is pathutil.Space.RESEARCH and attr == constants.IISTATUSATTRNAME:
        # Research folder status change. Validate.
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

    elif space is pathutil.Space.VAULT and attr == constants.IIVAULTSTATUSATTRNAME:
        if not user.is_admin(ctx, actor):
            return policy.fail('No permission to change vault status')

        current = vault.get_coll_vault_status(ctx, obj_name)

        ctx.iiPreVaultStatusTransition(obj_name, current.value, value)
        return policy.succeed()

    elif obj_type == '-C' and space is pathutil.Space.RESEARCH and unit.startswith(constants.UUUSERMETADATAROOT + '_'):
        # Research package metadata, set when saving the metadata form.
        # Allow if object is not locked.

        if (not folder.is_locked(ctx, obj_name)) or user.is_admin(ctx, actor):
            return policy.succeed()
        else:
            return policy.fail('Folder is locked')
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

    if pathutil.info(dst).space in [pathutil.Space.RESEARCH, pathutil.Space.VAULT]:
        return policy.fail('Metadata mod not allowed')


# imeta cp
@policy.require()
def py_acPreProcForModifyAVUMetadata_cp(ctx, _, t_src, t_dst, src, dst):
    actor = user.user_and_zone(ctx)
    if user.is_admin(ctx, actor):
        return policy.succeed()

    if t_dst not in ['-d', '-C']:
        return policy.succeed()

    if pathutil.info(dst).space in [pathutil.Space.RESEARCH, pathutil.Space.VAULT]:
        # Prevent imeta cp. Previously this was blocked by a buggy policy.
        # We now block this explicitly in research & vault because the action is
        # too difficult to reliably validate w.r.t. for example folder status transitions,
        # and no rules make use of this code path.
        return policy.fail('Metadata copy not allowed')

    return policy.succeed()


# This PEP is called after a AVU is added (option = 'add'), set (option =
# 'set') or removed (option = 'rm') in the research area or the vault. Post
# conditions defined in iiFolderStatusTransitions.r and iiVaultTransitions.r
# are called here.
@rule.make()
def py_acPostProcForModifyAVUMetadata(ctx, option, obj_type, obj_name, attr, value, unit):
    info = pathutil.info(obj_name)

    if attr == constants.IISTATUSATTRNAME and info.space is pathutil.Space.RESEARCH:
        status = constants.research_package_state.FOLDER.value if option in ['rm', 'rmw'] else value
        ctx.iiPostFolderStatusTransition(obj_name, str(user.user_and_zone(ctx)), status)

    elif attr == constants.IISTATUSATTRNAME and info.space is pathutil.Space.VAULT:
        ctx.iiPostVaultStatusTransition(obj_name, str(user.user_and_zone(ctx)), value)


# }}}
# ExecCmd {{{

@policy.require()
def py_acPreProcForExecCmd(ctx, cmd, args, addr, hint):

    actor = user.user_and_zone(ctx)

    # No restrictions for rodsadmin and priv group.
    if user.is_admin(ctx, actor):
        return policy.succeed()
    if user.is_member_of(ctx, 'priv-execcmd-all', actor):
        return policy.succeed()

    if not (hint == addr == ''):
        return policy.fail('Disallowed hint/addr in execcmd')

    # allow 'admin-*' scripts, iff first arg is the actor username&zone.
    if cmd.startswith('admin-'):
        if args == str(actor) or args.startswith(str(actor) + ' '):
            return policy.succeed()
        else:
            return policy.fail('Actor not given as first arg to admin- execcmd')

    # Allow scheduled scripts.
    if cmd.startswith('scheduled-'):
        return policy.succeed()

    return policy.fail('No execcmd privileges for this command')


@rule.make()
def pep_resource_modified_post(ctx, instance_name, _ctx, out):
    if instance_name not in config.resource_primary:
        return

    path = _ctx.map()['logical_path']
    zone = _ctx.map()['user_rods_zone']
    username = _ctx.map()['user_user_name']

    ctx.uuReplicateAsynchronously(path, instance_name, config.resource_replica)

    info = pathutil.info(path)

    try:
        # Import metadata if a metadata JSON file was changed.
        # Example matches:
        # "/tempZone/home/research-any/possible/path/to/yoda-metadata.json"
        # "/tempZone/home/vault-any/possible/path/to/yoda-metadata[123][1].json"
        # "/tempZone/home/datamanager-category/vault-path/to/yoda-metadata.json"
        if ((info.space in (pathutil.Space.RESEARCH, pathutil.Space.DATAMANAGER)
                and pathutil.basename(info.subpath) == constants.IIJSONMETADATA)
            or (info.space is pathutil.Space.VAULT
                # Vault jsons have a [timestamp] in the file name.
                and re.match(r'{}\[[^/]+\]\.{}$'.format(*map(re.escape, pathutil.chopext(constants.IIJSONMETADATA))),
                             pathutil.basename(info.subpath)))):
            # Path is a metadata file, ingest.
            log.write(ctx, 'metadata JSON <{}> modified by {}, ingesting'.format(path, username))
            ctx.rule_uu_meta_modified_post(path, username, zone)

    except Exception as e:
        # The rules on metadata are run synchronously and could fail.
        # Log errors, but continue with revisions.
        log.write(ctx, 'rule_uu_meta_modified_post failed: ' + str(e))

    ctx.uuResourceModifiedPostRevision(instance_name, zone, path)


@rule.make()
def py_acPostProcForObjRename(ctx, src, dst):
    # Update ACLs to give correct group ownership when an object is moved into
    # a different research- or grp- collection.
    info = pathutil.info(dst)
    if info.space is pathutil.Space.RESEARCH or info.group.startswith(constants.IIGRPPREFIX):
        if len(info.subpath) and info.group != pathutil.info(src).group:
            ctx.uuEnforceGroupAcl(dst)

# }}}
# }}}
