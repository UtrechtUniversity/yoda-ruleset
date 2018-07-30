
# \brief Write group data for all users to stdout.
#
def uuGetGroupData(rule_args, callback, rei):
    groups = {}

    #
    # first query: obtain a list of groups with group attributes
    #
    ret_val = callback.msiMakeGenQuery("USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE", "USER_TYPE = 'rodsgroup'", irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
	result = ret_val["arguments"][1]
	for row in range(result.rowCnt):
	    name = result.sqlResult[0].row(row)
	    attr = result.sqlResult[1].row(row)
	    value = result.sqlResult[2].row(row)

	    # create/update group with this information
	    try:
		group = groups[name]
	    except:
		group = {
		    "name": name,
		    "managers": [],
		    "members": [],
		    "read": []
	        }
		groups[name] = group
	    if attr == "description" or attr == "category" or attr == "subcategory":
		group[attr] = value
	    if attr == "manager":
		group["managers"].append(value)

	# continue with this query
	if result.continueInx == 0:
	    break
	ret_val = callback.msiGetMoreRows(query, result, 0)

    #
    # second query: obtain list of groups with memberships
    #
    ret_val = callback.msiMakeGenQuery("USER_GROUP_NAME, USER_NAME, USER_ZONE", "USER_TYPE != 'rodsgroup'", irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
	result = ret_val["arguments"][1]
	for row in range(result.rowCnt):
	    name = result.sqlResult[0].row(row)
	    user = result.sqlResult[1].row(row)
	    zone = result.sqlResult[2].row(row)

	    if name != user and name != "rodsadmin" and name != "public":
		user = user + "#" + zone
		if name.startswith("read-"):
		    # match read-* group with research-* or initial-* group.
		    name = name[5:]
		    try:
			# attempt to add to read list of research group
			group = groups["research-" + name]
			group["read"].append(user)
		    except:
			try:
			    # attempt to add to read list of initial group
			    group = groups["initial-" + name]
			    group["read"].append(user)
			except:
			    pass
		elif not name.startswith("vault-"):
		    # ordinary group
		    group = groups[name]
		    group["members"].append(user)

	# continue with this query
	if result.continueInx == 0:
	    break
	ret_val = callback.msiGetMoreRows(query, result, 0)

    # convert to json string and write to stdout
    callback.writeString("stdout", json.dumps(groups.values()))
