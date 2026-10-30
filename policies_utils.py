"""iRODS policy utility functions"""

__copyright__ = 'Copyright (c) 2024-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import ast
import re
from typing import List, Optional, Set, Tuple


from config import Config, config
from util import pathutil, rule, user
from util.genquery_col_constants import *


def should_transition_submitted_to_accepted_immediately(folder_path: str, datamanagers: List[Tuple[str, str]]) -> bool:
    """Determines whether a folder that is submitted should be transitioned to
       an "accepted" status immediately, without an approval step.

       :param folder_path: path of folder to be submitted.
       :param datamanagers: list of datamanagers

       :returns: boolean value. True if folder should be transitioned
                 to accepted status immediately, otherwise false.
    """
    space = pathutil.info(folder_path).space
    if space is pathutil.Space.RESEARCH:
        # Data manager approval is not needed if the category has no data managers
        return len(datamanagers) == 0
    elif space is pathutil.Space.DEPOSIT:
        # No approval is needed for data packages in deposit space
        return True
    else:
        # Yoda does not support submitting data packages outside research and deposit space.
        # Do not accept.
        return False


def is_safe_genquery_inp(genquery_inp: object) -> bool:
    """Checks if a GenQuery input matches Yoda policies

       :param genquery_inp: GenQueryInp object containing query information

       :returns: boolean value. True if query may be executed; false if query
                 should be rejected for security or safety reasons.
    """
    return _is_safe_genquery_inp(genquery_inp.selectInp, genquery_inp.sqlCondInp.inx)


def _column_in_select_inp(selectInp: Set[int], columns: Set[int]) -> bool:
    selectedInpHash = ast.literal_eval(str(selectInp))
    selected_columns  = selectedInpHash.keys()
    for column in columns:
        if column in selected_columns:
            return True
    return False


def _column_in_cond_inp(sqlCondInp: Set[int], columns: Set[int]) -> bool:
    condition_columns = ast.literal_eval(str(sqlCondInp))
    for column in columns:
        if column in condition_columns:
            return True
    return False


def _is_safe_genquery_inp(selectInp: Set[int], sqlCondInp: Set[int]) -> bool:
    # Defines groups of GenQuery columns
    dataobject_columns = {COL_D_DATA_ID, COL_D_COLL_ID, COL_DATA_NAME, COL_DATA_REPL_NUM,
                          COL_DATA_VERSION, COL_DATA_TYPE_NAME, COL_DATA_SIZE,
                          COL_D_RESC_NAME, COL_D_DATA_PATH, COL_D_OWNER_NAME, COL_D_OWNER_ZONE,
                          COL_D_REPL_STATUS, COL_D_DATA_STATUS, COL_D_DATA_CHECKSUM,
                          COL_D_EXPIRY, COL_D_MAP_ID, COL_D_COMMENTS, COL_D_CREATE_TIME, COL_D_MODIFY_TIME,
                          COL_DATA_MODE, COL_D_RESC_HIER, COL_D_RESC_ID}
    collection_columns = {COL_COLL_ID, COL_COLL_NAME, COL_COLL_PARENT_NAME,
                          COL_COLL_OWNER_NAME, COL_COLL_OWNER_ZONE,
                          COL_COLL_MAP_ID, COL_COLL_INHERITANCE, COL_COLL_COMMENTS,
                          COL_COLL_CREATE_TIME, COL_COLL_MODIFY_TIME,
                          COL_COLL_TYPE, COL_COLL_INFO1, COL_COLL_INFO2}
    resource_columns   = {COL_R_RESC_ID, COL_R_RESC_NAME, COL_R_ZONE_NAME, COL_R_TYPE_NAME, COL_R_CLASS_NAME,
                          COL_R_LOC, COL_R_VAULT_PATH, COL_R_FREE_SPACE, COL_R_RESC_INFO, COL_R_RESC_COMMENT,
                          COL_R_CREATE_TIME, COL_R_MODIFY_TIME, COL_R_RESC_STATUS,
                          COL_R_FREE_SPACE_TIME, COL_R_RESC_CHILDREN, COL_R_RESC_CONTEXT, COL_R_RESC_PARENT,
                          COL_R_RESC_PARENT_CONTEXT}
    user_columns       = {COL_USER_ID, COL_USER_NAME, COL_USER_TYPE, COL_USER_ZONE,
                          COL_USER_INFO, COL_USER_COMMENT, COL_USER_CREATE_TIME, COL_USER_MODIFY_TIME,
                          COL_USER_GROUP_ID, COL_USER_GROUP_NAME}

    dataobject_avu_columns = {COL_META_DATA_ATTR_NAME, COL_META_DATA_ATTR_VALUE, COL_META_DATA_ATTR_UNITS}
    collection_avu_columns = {COL_META_COLL_ATTR_NAME, COL_META_COLL_ATTR_VALUE, COL_META_COLL_ATTR_UNITS}
    resource_avu_columns = {COL_META_RESC_ATTR_NAME, COL_META_RESC_ATTR_VALUE, COL_META_RESC_ATTR_UNITS}
    user_avu_columns = {COL_META_USER_ATTR_NAME, COL_META_USER_ATTR_VALUE, COL_META_USER_ATTR_UNITS}

    uses_dataobject_columns = (_column_in_select_inp(selectInp, dataobject_columns)
                               or _column_in_cond_inp(sqlCondInp, dataobject_columns))
    uses_collection_columns = (_column_in_select_inp(selectInp, collection_columns)
                               or _column_in_cond_inp(sqlCondInp, collection_columns))
    uses_resource_columns = (_column_in_select_inp(selectInp, resource_columns)
                             or _column_in_cond_inp(sqlCondInp, resource_columns))
    uses_user_columns = (_column_in_select_inp(selectInp, user_columns)
                         or _column_in_cond_inp(sqlCondInp, user_columns))

    uses_dataobject_avu_columns = (_column_in_select_inp(selectInp, dataobject_avu_columns)
                                   or _column_in_cond_inp(sqlCondInp, dataobject_avu_columns))
    uses_collection_avu_columns = (_column_in_select_inp(selectInp, collection_avu_columns)
                                   or _column_in_cond_inp(sqlCondInp, collection_avu_columns))
    uses_resource_avu_columns = (_column_in_select_inp(selectInp, resource_avu_columns)
                                 or _column_in_cond_inp(sqlCondInp, resource_avu_columns))
    uses_user_avu_columns = (_column_in_select_inp(selectInp, user_avu_columns)
                             or _column_in_cond_inp(sqlCondInp, user_avu_columns))

    if uses_dataobject_avu_columns and not (uses_collection_columns or uses_dataobject_columns):
        return False
    elif uses_collection_avu_columns and not uses_collection_columns:
        return False
    elif uses_resource_avu_columns and not (uses_resource_columns
                                            or uses_collection_columns
                                            or uses_dataobject_columns):
        return False
    elif uses_user_avu_columns and not uses_user_columns:
        return False
    else:
        return True


# Determine whether changes to data objects on a particular resource need
# to trigger policies (e.g. asynchronous replication) by default.
def should_resource_trigger_policies(config: Config, resource: str) -> bool:
    if resource in config.resource_primary:
        return True

    if resource in config.resource_vault:
        return True

    for pattern in config.resource_trigger_pol:
        if re.match(pattern, resource):
            return True

    return False


# Determine whether resource should be exempt from policies (currently only for asynchronous replication)
def should_resource_be_replication_exempt(config: Config, resource: str) -> bool:
    exempt_list = config.resource_repl_exempt
    if exempt_list:
        for pattern in exempt_list:
            if pattern in resource:
                return True

    return False


def format_client_description(option: str) -> str:
    """Format the client option string for logging.

    Only a limited set of characters is allowed; anything else is replaced by a
    placeholder to prevent log injection.

    :param option: Client option string as provided by the connecting client

    :returns: A client description, or 'client: <filtered>' for unexpected input
    """
    if re.match(r'^[A-Za-z0-9,\./ \-;]+$', option):
        # Some client names like GoCommands have trailing semicolons. Strip those.
        if option.endswith(';'):
            return 'client: ' + option[:-1]
        return 'client: ' + option
    else:
        return 'client: <filtered>'


def check_anonymous_access_allowed(ctx: rule.Context, address: str) -> bool:
    """Check if access to the anonymous account is allowed from a particular network
       address. Non-local access to the anonymous account should only be allowed from
       DavRODS servers, for security reasons.

    :param ctx:  Combined type of a callback and rei struct
    :param address: Network address to check

    :returns: True if access from this network address is allowed; otherwise False
    """
    permit_list = ["127.0.0.1"] + config.remote_anonymous_access
    return address in permit_list


def check_max_connections_exceeded(ctx: rule.Context) -> bool:
    """Check if user exceeds the maximum number of connections.

    :param ctx: Combined type of a callback and rei struct

    :returns: True if maximum number of connections is exceeded; otherwise False
              Also returns False if the maximum number of connections check has been
              disabled, or if the maximum number does not apply to the present user.
    """
    if not config.user_max_connections_enabled:
        return False
    elif user.name(ctx) in ['anonymous', 'rods']:
        return False
    else:
        return user.number_of_connections(ctx) > config.user_max_connections_number


def get_session_refusal_reason(ctx: rule.Context, session_map: dict) -> Optional[str]:
    """Check whether a session should be refused before the client authenticates.
       These checks apply regardless of which authentication API the client uses.

    :param ctx:         Combined type of a callback and rei struct
    :param session_map: Session variables map of the agent

    :returns: Reason for refusing the session, or None if the session is allowed
    """
    proxy_user = session_map['proxy_user']
    client_user = session_map['client_user']
    client_address = session_map['connection']['client_address']

    # Check the proxy user, since that is the user that authenticates. The authentication
    # PEPs verify that it matches the user in the authentication request. The client user
    # is not checked: iRODS only allows a proxy user to act on behalf of a different client
    # user if the proxy user is a rodsadmin. This is the case for server-to-server
    # connections, which originate from other servers in the zone.
    if (proxy_user['user_name'] == 'anonymous'
            and not check_anonymous_access_allowed(ctx, client_address)):
        return f'Refused access to anonymous account from address {client_address}.'

    if check_max_connections_exceeded(ctx):
        return f'Refused access for {client_user["user_name"]}#{client_user["irods_zone"]}, max connections exceeded.'

    return None


def is_forwarded_pam_auth_request(proxy_user_data: dict,
                                  auth_scheme: Optional[str],
                                  auth_operation: Optional[str]) -> bool:
    """Check whether an authentication framework (API 110000) request is a PAM password
       check.

    The consumer forwards such requests over a server-to-server connection on which it
    has already authenticated with the service account, so the proxy user differs from
    the authenticating user. We rely on the privilege level rather than the proxy user
    name, because the name comes from the startup pack and has not been verified until
    the proxy user has authenticated.

    :param proxy_user_data: Proxy user data from the session variables
    :param auth_scheme:     Authentication scheme of the request
    :param auth_operation:  Authentication operation of the request

    :returns: Boolean indicating whether this is a forwarded PAM password check
    """
    # Refers to rodsadmin privileges in local zone
    LOCAL_PRIV_USER_AUTH = 5
    return (proxy_user_data['authentication_info']['privilege_level'] == LOCAL_PRIV_USER_AUTH
            and auth_scheme == 'pam_password'
            and auth_operation == 'auth_agent_auth_request')
