from datetime import datetime

def uuMetaAdd(callback, objType, objName, attribute, value):
    keyValPair  = callback.msiString2KeyValPair(attribute + "=" + value, irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiSetKeyValuePairsToObj(keyValPair, objName, objType)

# \brief Persist a data request to disk.
#
# \param[in] data       JSON-formatted contents of the data request.
# \param[in] proposalId Unique identifier of the research proposal.
#
def submitDatarequest(callback, data, proposalId):

    # Create subcollection
    zonePath = '/tempZone/home/datarequests-research/'
    proposalPath = zonePath + proposalId
    collPath = proposalPath + '/datarequests'
    callback.msiCollCreate(collPath, 1, 0)

    # Write data request data to disk  
    timestamp = datetime.now().strftime('%s')
    filePath = collPath + '/' + timestamp + '.json'
    ret_val = callback.msiDataObjCreate(filePath, "", 0)
    fileDescriptor = ret_val['arguments'][2]
    callback.msiDataObjWrite(fileDescriptor, data, 0)
    callback.msiDataObjClose(fileDescriptor, 0)

    # Set the status metadata field to "submitted"
    uuMetaAdd(callback, "-d", filePath, "status", "submitted")

    # Set permissions for certain groups on the subcollection
    callback.msiSetACL("recursive", "write", "datarequests-research-datamanagers", collPath)
    callback.msiSetACL("recursive", "write", "datarequests-research-board-of-directors", collPath)

# \brief Retrieve a data request.
#
# \param[in] requestId Unique identifier of the data request.
#
def getDatarequest(callback, requestId):

    fileName = requestId + '.json'

    # Get the size of the datarequest JSON file and the request's status
    results = []
    rows = row_iterator(["DATA_SIZE", "COLL_NAME", "META_DATA_ATTR_VALUE"],
                        "DATA_NAME = '%s'" % (fileName),
                        AS_DICT,
                        callback)
    for row in rows:
       collName = row['COLL_NAME']
       filePath = collName + '/' + fileName
       proposalId = collName.split('/')[-2]
       dataSize = row['DATA_SIZE']
       requestStatus = row['META_DATA_ATTR_VALUE']

    # Get the contents of the datarequest JSON file
    ret_val = callback.msiDataObjOpen("objPath=%s" % filePath, 0)
    fileDescriptor = ret_val['arguments'][1]
    ret_val = callback.msiDataObjRead(fileDescriptor, dataSize, irods_types.BytesBuf())
    fileBuffer = ret_val['arguments'][2]
    callback.msiDataObjClose(fileDescriptor, 0)
    requestJSON = ''.join(fileBuffer.buf)

    return {'proposalId': proposalId, 'requestJSON': requestJSON, 'requestStatus': requestStatus}

def uuSubmitDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatarequest(callback, rule_args[0], rule_args[1])))

def uuGetDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getDatarequest(callback, rule_args[0])))
