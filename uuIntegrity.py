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


DataObject = namedtuple('DataObject', ['id', 'name', 'size', 'checksum', 'coll_name', 'resc_path', 'resc_loc'])
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


def checkDataObjectRemote(rule_args, callback, rei):
    file_path = str(rule_args[0])
    file_size = int(rule_args[1])
    file_checksum = str(rule_args[2])

    # Check if file exists in vault.
    if not os.path.isfile(file_path):
        callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.NOT_EXISTING)))
        return

    # Check if file size matches.
    if int(file_size) != os.path.getsize(file_path):
        callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.FILE_SIZE_MISMATCH)))
        return

    # Check if checksum exists.
    if not file_checksum:
        callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.NO_CHECKSUM)))
        return

    # Open file and compute checksum.
    try:
        f = open(file_path, 'rb')
    except OSError as e:
        if e.errno == errno.EACCES:
            callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.ACCESS_DENIED)))
            return
        else:
            raise
    else:
        # Determine if checksum is md5 or sha256.
        if file_checksum.startswith("sha2:"):
            checksum = file_checksum[5:]
            hsh = hashlib.sha256()
        else:
            checksum = file_checksum
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
        callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.CHECKSUM_MISMATCH)))
        return

    callback.writeString("serverLog", "%s: %s" % (file_path, str(Status.OK)))


def checkDataObjectIntegrity(callback, data_id):
    # Obtain all replicas of a data object.
    ret_val = callback.msiMakeGenQuery(
        "DATA_ID, DATA_NAME, DATA_SIZE, DATA_CHECKSUM, COLL_NAME, RESC_VAULT_PATH, RESC_LOC",
        "DATA_ID = '%s'" % data_id,
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())

    # Loop through all replicas.
    while True:
        result = ret_val["arguments"][1]
        for row in range(result.rowCnt):
            data_object = DataObject._make([result.sqlResult[0].row(row),
                                            result.sqlResult[1].row(row),
                                            result.sqlResult[2].row(row),
                                            result.sqlResult[3].row(row),
                                            result.sqlResult[4].row(row),
                                            result.sqlResult[5].row(row),
                                            result.sqlResult[6].row(row)])

            # Build file path to data object.
            coll_name = os.path.join(*(data_object.coll_name.split(os.path.sep)[2:]))
            file_path = data_object.resc_path + "/" + coll_name + "/" + data_object.name

            # Check integrity on the resource.
            callback.remoteExec(
                "%s" % data_object.resc_loc,
                "",
                "checkDataObjectRemote('%s', '%s', '%s')" % (file_path, data_object.size, data_object.checksum),
                ""
            )

        # Continue with this query.
        if result.continueInx == 0:
            break
        ret_val = callback.msiGetMoreRows(query, result, 0)
    callback.msiCloseGenQuery(query, result)


def uuCheckDataObjectIntegrity(rule_args, callback, rei):
    checkDataObjectIntegrity(callback, rule_args[0])


# Check integrity of one batch of data objects in the vault.
def checkVaultIntegrityBatch(callback, rods_zone, data_id, batch, pause):
    import time

    # Go through data in the vault, ordered by DATA_ID.
    ret_val = callback.msiMakeGenQuery(
        "ORDER(DATA_ID)",
        "COLL_NAME like '/%s/home/vault-%%' AND DATA_ID >= '%d'" % (rods_zone, data_id),
        irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    result = ret_val["arguments"][1]

    if result.rowCnt != 0:
        # Check each data object in batch.
        for row in range(min(batch, result.rowCnt)):
            data_id = int(result.sqlResult[0].row(row))
            checkDataObjectIntegrity(callback, data_id)

            # Sleep briefly between checks.
            time.sleep(pause)

        # The next data object to check must have a higher DATA_ID.
        data_id = data_id + 1
    else:
        # All done.
        data_id = 0
    callback.msiCloseGenQuery(query, result)

    return data_id


# \brief Check integrity of all data objects in the vault.
# \param[in] data_id  first DATA_ID to check
# \param[in] batch    batch size, <= 256
# \param[in] pause    pause between checks (float)
# \param[in] delay    delay between batches in seconds
#
def uuCheckVaultIntegrity(rule_args, callback, rei):
    import session_vars

    data_id = int(rule_args[0])
    batch = int(rule_args[1])
    pause = float(rule_args[2])
    delay = int(rule_args[3])
    rods_zone = session_vars.get_map(rei)["client_user"]["irods_zone"]

    # Check one batch of vault data.
    data_id = checkVaultIntegrityBatch(callback, rods_zone, data_id, batch, pause)

    if data_id != 0:
        # Check the next batch after a delay.
        callback.delayExec(
            "<PLUSET>%ds</PLUSET>" % delay,
            "uuCheckVaultIntegrity('%d', '%d', '%f', '%d')" % (data_id, batch, pause, delay),
            "")
