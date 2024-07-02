# -*- coding: utf-8 -*-
"""iRODS policy utility functions"""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import ast

from util.genquery_col_constants import *


def is_safe_genquery_inp(genquery_inp):
    """Checks if a GenQuery input matches Yoda policies

       :param genquery_inp: GenQueryInp object containing query information

       :returns: boolean value. True if query may be executed; false if query
                 should be rejected for security or safety reasons.
    """
    return _is_safe_genquery_inp(genquery_inp.selectInp, genquery_inp.sqlCondInp)


def _column_in_select_inp(selectInp, columns):
    selectedInpHash = ast.literal_eval(str(selectInp))
    selected_columns  = selectedInpHash.keys()
    for column in columns:
        if column in selected_columns:
            return True
    return False


def _column_in_cond_inp(sqlCondInp, columns):
    condition_data = ast.literal_eval(str(sqlCondInp))
    condition_columns = map(lambda c: c[0], condition_data)
    for column in columns:
        if column in condition_columns:
            return True
    return False


def _is_safe_genquery_inp(selectInp, sqlCondInp):
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
