import itertools

import genquery

from util import *


def chop_checksum(checksum):
    """Chop iRODS checksum in checksum type and checksum string.

    Checksum format is ({type}:){checksum}, if type is missing then it is "md5".

    :param checksum: iRODS checksum string
    :returns: type checksum
    """
    checksum_split = checksum.split(":")

    if len(checksum_split) > 1:
        type = checksum_split[0]
        checksum = checksum_split[1]

    return type, checksum


def intake_generate_dataset_checksums(ctx, dataset_path, checksum_file):
    """"Generate data object with all checksums of a dataset.

    :param ctx:    Combined type of a callback and rei struct
    :param dataset_path:  Root collection of dataset to be indexed
    :param checksum_file: Data object to write checksums to
    """
    q_root = genquery.row_iterator("COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE",
                                   "COLL_NAME = '{}'".format(dataset_path),
                                   genquery.AS_LIST, ctx)

    q_sub = genquery.row_iterator("COLL_NAME, DATA_NAME, DATA_CHECKSUM, DATA_SIZE",
                                  "COLL_NAME like '{}/%'".format(dataset_path),
                                  genquery.AS_LIST, ctx)

    # Create checksums file.
    checksums = ""
    for row in itertools.chain(q_root, q_sub):
        type, checksum = chop_checksum(row[2])
        checksums += "{} {} {} {}/{}\n".format(type, checksum, row[3], row[0], row[1])

    # Write checksums file.
    data_object.write(ctx, checksum_file, checksums)
