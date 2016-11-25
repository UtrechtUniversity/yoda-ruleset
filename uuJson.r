# \brief uuKvList2JSON convert a list of keyvalue objects into JSON string
# \param[in] kvpList	list of key-value-pairs to convert to JSON
# \param[out] json_str	String containing JSON
# \param[out] size	Number of JSON objects in JSON array
uuKvpList2JSON(*kvpList, *json_str, *size) {
	*json_str = "[]";
	*size = 0;
	*listsize = size(*kvpList);
	#| writeLine("stdout", *listsize);

	foreach(*kvp in *kvpList) {	
		*json_obj = "";	
		msi_json_objops(*json_obj, *kvp, "set");
        	msi_json_arrayops(*json_str, *json_obj, "add", *size);
	}
}
