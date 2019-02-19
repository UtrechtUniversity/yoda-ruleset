# \file      iiVault.py
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json


# \brief Retrieve lists of preservable file formats on the system.
#
# \return Lists of preservable file formats
#
def getPreservableFormatsLists(callback):
    return {'DANS': 'DANS Preservable formats', '4TU': '4TU Preservable formats'}


# \brief Retrieve all unpreservable files in a folder.
#
# \param[in] folder Path of folder to check.
# \param[in] list   Name of preservable file format list.
#
# \return List of unpreservable files.
#
def getUnpreservableFilesList(callback, folder, list):
    return ['pdf', 'svg', 'tiff']


# \brief Write preservable file formats lists to stdout.
#
def iiGetPreservableFormatsListsJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getPreservableFormatsLists(callback)))


# \brief Write unpreservable files in folder to stdout.
#
# \param[in] rule_args[0] Path of folder to check.
# \param[in] rule_args[1] Name of preservable file format list.
#
def iiGetUnpreservableFilesListJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getUnpreservableFilesList(callback, rule_args[0], rule_args[1])))
