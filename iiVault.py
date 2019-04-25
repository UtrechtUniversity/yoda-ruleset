# \file      iiVault.py
# \brief     Functions to copy packages to the vault and manage permissions of vault packages.
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import json
import os


# \brief Retrieve lists of preservable file formats on the system.
#
# \return Lists of preservable file formats
#
def getPreservableFormatsLists(callback):
    preservableLists = {}
    zoneName = ""
    clientZone = callback.uuClientZone(zoneName)['arguments'][0]

    # Retrieve all preservable file formats lists on the system.
    ret_val = callback.msiMakeGenQuery(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME = '/{}/yoda/file_formats' AND DATA_NAME like '%%.json'".format(clientZone),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            data_name = result.sqlResult[0].row(row)
            coll_name = result.sqlResult[1].row(row)

            # Retrieve filename and name of list.
            filename, file_extension = os.path.splitext(data_name)
            json = parseJson(callback, coll_name + "/" + data_name)

            # Add to list of preservable file formats.
            preservableLists[filename] = json

        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    return {'lists': preservableLists}


# \brief Retrieve all unpreservable files in a folder.
#
# \param[in] folder Path of folder to check.
# \param[in] list   Name of preservable file format list.
#
# \return List of unpreservable files.
#
def getUnpreservableFiles(callback, folder, list):
    zoneName = ""
    clientZone = callback.uuClientZone(zoneName)['arguments'][0]

    # Retrieve JSON list of preservable file formats.
    json = parseJson(callback, "/" + clientZone + "/yoda/file_formats/" + list + ".json")
    preservableFormats = json['formats']
    unpreservableFormats = []

    # Retrieve all files in collection.
    ret_val = callback.msiMakeGenQuery(
        "DATA_NAME, COLL_NAME",
        "COLL_NAME like '%s%%'" % (folder),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            data_name = result.sqlResult[0].row(row)
            filename, file_extension = os.path.splitext(data_name)

            # Convert to lowercase and remove dot.
            file_extension = (file_extension.lower())[1:]

            # Check if extention is in preservable format list.
            if (file_extension not in preservableFormats):
                unpreservableFormats.append(file_extension)

        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)

    # Remove duplicate file formats.
    output = []
    for x in unpreservableFormats:
        if x not in output:
            output.append(x)

    return {'formats': output}



# \brief Write preservable file formats lists to stdout.
#
def iiGetPreservableFormatsListsJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getPreservableFormatsLists(callback)))


# \brief Write unpreservable files in folder to stdout.
#
# \param[in] rule_args[0] Path of folder to check.
# \param[in] rule_args[1] Name of preservable file format list.
#
def iiGetUnpreservableFilesJson(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getUnpreservableFiles(callback, rule_args[0], rule_args[1])))
