import json
import irods_types
from datetime import datetime
from genquery import ( row_iterator, paged_iterator, AS_DICT, AS_LIST )

def uuMetaAdd(callback, objType, objName, attribute, value):
    keyValPair  = callback.msiString2KeyValPair(attribute + "=" + value, irods_types.KeyValPair())['arguments'][1]
    retval = callback.msiSetKeyValuePairsToObj(keyValPair, objName, objType)


# \brief Persist a research proposal to disk.
#
# \param[in] data    JSON-formatted contents of the research proposal.
#
def submitProposal(callback, data):
    # Create collection
    zonePath = '/tempZone/home/datarequests-research/'
    timestamp = datetime.now().strftime('%s')
    collPath = zonePath + str(timestamp)
    callback.msiCollCreate(collPath, 1, 0)

    # Write proposal data as JSON to the created collection
    proposalPath = collPath + "/proposal.json"
    ret_val = callback.msiDataObjCreate(proposalPath, "", 0)
    fileDescriptor = ret_val['arguments'][2]
    callback.msiDataObjWrite(fileDescriptor, data, 0)
    callback.msiDataObjClose(fileDescriptor, 0)

    # Set the status metadata field of the proposal to "submitted"
    uuMetaAdd(callback, "-d", proposalPath, "status", "submitted")

    # Set permissions for certain groups on the subcollection
    callback.msiSetACL("recursive", "write", "datarequests-research-datamanagers", collPath)
    callback.msiSetACL("recursive", "write", "datarequests-research-board-of-directors", collPath) 

# \brief Set the status of a submitted research proposal to "approved"
#
# \param[in] researchProposalId Unique identifier of the research proposal.
#
def approveProposal(callback, researchProposalId):
    proposalPath = "/tempZone/home/datarequests-research/" + researchProposalId + "/proposal.json"
    uuMetaAdd(callback, "-d", proposalPath, "status", "approved")

# \brief Retrieve a research proposal.
#
# \param[in] researchProposalId Unique identifier of the research proposal.
#
# \return The JSON-formatted contents of the research proposal and the status
#         of the research proposal.
#
def getProposal(callback, researchProposalId):

    # Set collection path and file path
    collPath = '/tempZone/home/datarequests-research/' + researchProposalId
    filePath = collPath + '/proposal.json'

    # Get the size of the proposal JSON file and the status of the proposal
    results = []
    rows = row_iterator(["DATA_SIZE", "META_DATA_ATTR_VALUE"],
                        "COLL_NAME = '%s' and DATA_NAME = '%s'" % (collPath, 'proposal.json'),
                        AS_DICT,
                        callback)
    for row in rows:
       dataSize = row['DATA_SIZE']
       proposalStatus = row['META_DATA_ATTR_VALUE']

    # Get the contents of the proposal JSON file
    ret_val = callback.msiDataObjOpen("objPath=%s" % filePath, 0)
    fileDescriptor = ret_val['arguments'][1]
    ret_val = callback.msiDataObjRead(fileDescriptor, dataSize, irods_types.BytesBuf())
    fileBuffer = ret_val['arguments'][2]
    callback.msiDataObjClose(fileDescriptor, 0)
    proposalJSON = ''.join(fileBuffer.buf)

    return {'proposalJSON': proposalJSON, 'proposalStatus': proposalStatus}

# \brief Retrieve descriptive information of a number of research proposals.
#        This is used to render a paginated table of research proposals.
#
# \param[in] limit  The number of proposals to return.
# \param[in] offset Offset used for table pagination.
#
# \return List of descriptive information about a number of research proposals.
#
def DRAFTgetProposals(callback, limit, offset):
    # Query iRODS to get a list of submitted proposals (i.e. subcollections
    # of the datarequests-research collection)
    path = '/tempZone/home/datarequests-research';
    fields = ["COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE"];
    conditions = [callback.uucondition("COLL_PARENT_NAME", "=", path), callback.uucondition("DATA_NAME", "=", "proposal.json")];
    orderby = "COLL_NAME";
    ascdesc = "asc";

    callback.uuPaginatedQuery(fields, conditions, orderby, ascdesc, limit, offset, 0, 0, 0);
    # uuKvpList2JSON(kvpList, result, size);

def uuSubmitProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(submitProposal(callback, rule_args[0])))

def uuApproveProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(approveProposal(callback, rule_args[0])))

def uuGetProposal(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getProposal(callback, rule_args[0])))

def DRAFTuuGetProposals(rule_args, callback, rei):
    callback.writeString("stdout", json.dumps(getProposals(callback, rule_args[0], rule_args[1])))
