def uuGetGroupData(rule_args, callback, rei):
    import irods_types
    import json

    groups = {}

    ret_val = callback.msiMakeGenQuery("USER_GROUP_NAME, META_USER_ATTR_NAME, META_USER_ATTR_VALUE", "USER_TYPE = 'rodsgroup'", irods_types.GenQueryInp())
    query = ret_val["arguments"][2]

    ret_val = callback.msiExecGenQuery(query, irods_types.GenQueryOut())
    while True:
	result = ret_val["arguments"][1]
	for row in range(result.rowCnt):
	    name = result.sqlResult[0].row(row)
	    attr = result.sqlResult[1].row(row)
	    value = result.sqlResult[2].row(row)

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

	if result.continueInx == 0:
	    break
	ret_val = callback.msiGetMoreRows(query, result, 0)

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
		    name = name[5:]
		    try:
			group = groups["research-" + name]
			group["read"].append(user)
		    except:
			try:
			    group = groups["initial-" + name]
			    group["read"].append(user)
			except:
			    pass
		elif not name.startswith("vault-"):
		    group = groups[name]
		    group["members"].append(user)

	if result.continueInx == 0:
	    break
	ret_val = callback.msiGetMoreRows(query, result, 0)

    callback.writeString("stdout", json.dumps(groups.values()))
