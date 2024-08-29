# -*- coding: utf-8 -*-
"""Functions for handling schema updates within any yoda-metadata file."""

__copyright__ = 'Copyright (c) 2018-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__all__ = ['rule_batch_vault_packages_troubleshoot']

import json
import os
import re
import time

import genquery
import session_vars
import jsonutil
import meta
import meta_form
import schema
import schema_transformations
from util import avu
from util import *
@rule.make(inputs=[], outputs=[0])
def rule_batch_vault_packages_troubleshoot(ctx):
    """Diagnose the data pakge has avus expected

    :param ctx:      Combined type of a callback and rei struct
    """
    print("starts rule_batch_vault_packages_troubleshoot")

    #error_dict = {}

    # example uses default-3 schema
    #coll_name = '/tempZone/home/vault-default-3/research-default-3[1722327809]'

    # yoda-metadata vs AVUs check,
    # 1. get latest yoda-metadata of the package

    # metadata_path = meta.get_latest_vault_metadata_path(ctx, coll_name)
    # print("metadata_path", metadata_path)

    # metadata = jsonutil.read(ctx, metadata_path)
    # print("metadata", metadata)

        # continue
    # 2. get avus of the package
    # result = [(m.attr, m.value, m.unit) for m in avu.of_coll(ctx, coll_name)]
    # print("avus result", result)


    # 3. if all yoda-metadata is presented in avus
    # 3. if no save it to ?

    # system-metadata check
    # 1. for the ground truth data package (same default-3)
    # 2. get avus of it (exclude )
