# \file      uuProposals.r
# \brief     Functions to handle proposals (only methods that haven't been
#            rewritten in Python yet).
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Retrieve descriptive information of a number of research proposals.
#        This is used to render a paginated table of research proposals.
#
# \param[in] limit  The number of proposals to return.
# \param[in] offset Offset used for table pagination.
#
# \return List of descriptive information about a number of research proposals.
#
uuGetProposals(*limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", "status"));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}


# \brief Same as uuGetProposals, but with a different META_DATA_ATTR_NAME as
#        query condition and fewer return fields. This is a necessary hack,
#        because the iRODS query language does not have an OR operator
#
# \param[in] limit         The number of proposals to return.
# \param[in] offset        Offset used for table pagination.
# \param[in] attributeName The attribute whose value should be returned
#
# \return List of descriptive information about a number of research proposals.
#
uuGetProposalsAdditionalFields(*limit, *offset, *attributeName, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", *attributeName));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}
