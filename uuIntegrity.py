# \file      uuIntegrity.py
# \brief     Functions for data integrity.
# \author    Lazlo Westerhof
# \author    Felix Croes
# \copyright Copyright (c) 2018 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

import os.path
from collections import namedtuple
from enum import Enum
import hashlib
import base64


DataObject = namedtuple('DataObject', ['id', 'name', 'size', 'checksum', 'coll_name', 'resc_path'])
CHUNK_SIZE = 8192


class Status(Enum):
    OK = 0
    NOT_EXISTING = 1        # File registered in iRODS but not found in vault
    FILE_SIZE_MISMATCH = 2  # File sizes do not match between database and vault
    CHECKSUM_MISMATCH = 3   # Checksums do not match between database and vault
    ACCESS_DENIED = 4       # This script was denied access to the file
    NO_CHECKSUM = 5         # iRODS has no checksum registered

    def __repr__(self):
        return self.name


def checkDataObjectIntegrity(callback, data_id):
    # Obtain all replicas of a data object.
    ret_val = callback.msiMakeGenQuery(
        "DATA_ID, DATA_NAME, DATA_SIZE, DATA_CHECKSUM, COLL_NAME, RESC_VAULT_PATH",
        "DATA_ID = '%s'" % data_id,
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())

    # Loop through all replicas.
    status = Status.OK
    prev_data_object = None
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            # Integrity check failed.
            if status != Status.OK:
                break

            data_object = DataObject._make([result.sqlResult[0].row(row),
                                           result.sqlResult[1].row(row),
                                           result.sqlResult[2].row(row),
                                           result.sqlResult[3].row(row),
                                           result.sqlResult[4].row(row),
                                           result.sqlResult[5].row(row)])

            # Build file path to data object.
            coll_name = os.path.join(*(data_object.coll_name.split(os.path.sep)[2:]))
            file_path = data_object.resc_path + "/" + coll_name + "/" + data_object.name

            # Check if file exists in vault.
            if not os.path.isfile(file_path):
                status = Status.NOT_EXISTING
                break

            # Check if file size matches.
            if int(data_object.size) != os.path.getsize(file_path):
                status = Status.FILE_SIZE_MISMATCH
                break

            # Check if checksum exists.
            if not data_object.checksum:
                status = Status.NO_CHECKSUM
                break

            # Open file and compute checksum.
            try:
                f = open(file_path, 'rb')
            except OSError as e:
                if e.errno == errno.EACCES:
                    status = Status.ACCESS_DENIED
                    break
                else:
                    raise
            else:
                # Determine if checksum is md5 or sha256.
                if data_object.checksum.startswith("sha2:"):
                    checksum = data_object.checksum[5:]
                    hsh = hashlib.sha256()
                else:
                    hsh = hashlib.md5()

                # Compute checksum.
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if chunk:
                        hsh.update(chunk)
                    else:
                        break

                # iRODS stores md5 hashes plain and the sha256 hash base64 encoded.
                if hsh.name == 'md5':
                    computed_checksum = hsh.digest()
                else:
                    computed_checksum = base64.b64encode(hsh.digest())
                f.close()

            # Check if checksum matches.
            if checksum != computed_checksum:
                status = Status.CHECKSUM_MISMATCH
                break

            # Store data object to compare with next replica.
            prev_data_object = data_object

            # Compare with previous replica.
            if prev_data_object:
                # Check if checksum matches.
                if data_object.checksum != prev_data_object.checksum:
                    status = Status.CHECKSUM_MISMATCH
                    break

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)
    callback.writeString("serverLog", str(status))


def uuCheckDataObjectIntegrity(rule_args, callback, rei):
    checkDataObjectIntegrity(callback, rule_args[0])


# check integrity of all data objects in the vault
def checkVaultIntegrity(callback, rods_zone, data_id):
    import time

    ret_val = callback.msiMakeGenQuery(
        "ORDER(DATA_ID)",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_ID >= '%d'" % (rods_zone, data_id),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]
    if result.rowCnt == 0:
        callback.msiCloseGenQuery(query, result)
        return 0

    for row in range(result.rowCnt):
        data_id = int(result.sqlResult[0].row(row))
        checkDataObjectIntegrity(callback, data_id)
        time.sleep(0.5)
    callback.msiCloseGenQuery(query, result)

    return data_id + 1


def uuCheckVaultIntegrity(rule_args, callback, rei):
    import session_vars

    data_id = int(rule_args[0])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    data_id = checkVaultIntegrity(callback, rods_zone, data_id)

    if data_id != 0:
        callback.delayExec(
            "<PLUSET>1m</PLUSET>",
            "uuCheckVaultIntegrity('%d')" % data_id,
            "")
