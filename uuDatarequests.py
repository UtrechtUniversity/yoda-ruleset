from datetime import datetime

def uuMetaAdd(callback, objType, objName, attribute, value):
    keyValPair  = callback.msiString2KeyValPair(attribute + "=" + value, irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiSetKeyValuePairsToObj(keyValPair, objName, objType)

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

def uuSubmitDatarequest(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitDatarequest(callback, rule_args[0], rule_args[1])))
