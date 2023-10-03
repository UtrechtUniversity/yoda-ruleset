"""This file contains an interface to the spooling subsystem. The spooling system can be used to store
   temporary data for batch processing. The intended use case is that one job collects data to be processed
   and stores it in the spooling system, while another job retrieves the data and processes it.

   The current implementation does not have confirmations. It assumes that after spool data has been retrieved
   from the spool system it is either processed, or any errors during processing will be taken
   care of outside the spooling system (e.g. by having the job that collects data for the spooling system
   re-submit spool data that has not been processed for a retry).

   It is assumed that functions that use the spool subsystem take care of authorization and logging.
"""

import os

import persistqueue
import persistqueue.serializers.json

import constants


def get_spool_data(process):
    """Retrieves one data object for a given batch process for processing.
       This function is non-blocking.

    :param process:      Spool process name (see util.constants for defined names)

    :returns: Spool data object, or None if there is no spool data for this process
    """
    _ensure_spool_process_initialized(process)
    q = _get_spool_queue(process)

    try:
        result = q.get(block=False)
        q.task_done()
    except persistqueue.exceptions.Empty:
        result = None

    return result


def put_spool_data(process, data_list):
    """Stores data structures in the spooling subsystem for batch processing.

    :param process:      Spool process name (see util.constants for defined names)
    :param data_list:    List (or other iterable) of arbitrary serializable data objects to store
                         in the spooling system
    """
    _ensure_spool_process_initialized(process)
    q = _get_spool_queue(process)
    for data in data_list:
        q.put(data)


def has_spool_data(process):
    """ Checks whether there any data objects in the spool system for a given process

    :param process:      Spool process name (see util.constants for defined names)

    :returns:            Boolean value that represents whether there is any spool data
                         present for this process
    """
    return num_spool_data(process) > 0


def num_spool_data(process):
    """ Returns the number of items in the spool system for a given process

    :param process:      Spool process name (see util.constants for defined names)

    :returns:            The number of data items in the spool system for this process
    """
    _ensure_spool_process_initialized(process)
    return _get_spool_queue(process).qsize()


def _get_spool_directory(process):
    if process in constants.SPOOL_PROCESSES:
        return os.path.join(constants.SPOOL_MAIN_DIRECTORY, process, "spool")
    else:
        raise Exception("Spool process {} not found.".format(process))


def _get_temp_directory(process):
    if process in constants.SPOOL_PROCESSES:
        return os.path.join(constants.SPOOL_MAIN_DIRECTORY, process, "tmp")
    else:
        raise Exception("Spool process {} not found.".format(process))


def _get_spool_queue(process):
    directory = _get_spool_directory(process)
    # JSON serialization is used to make it easier to examine spooled objects manually
    return persistqueue.Queue(directory,
                              tempdir=_get_temp_directory(process),
                              serializer=persistqueue.serializers.json,
                              chunksize=1)


def _ensure_spool_process_initialized(process):
    if process not in constants.SPOOL_PROCESSES:
        raise Exception("Spool process {} not found.".format(process))

    for directory in [constants.SPOOL_MAIN_DIRECTORY,
                      os.path.join(constants.SPOOL_MAIN_DIRECTORY, process),
                      _get_spool_directory(process),
                      _get_temp_directory(process)]:
        if not os.path.exists(directory):
            os.mkdir(directory)
