# \brief uuKvList2JSON convert a list of key-value-pair objects into a JSON string
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

# \brief uuKvp2JSON  convert a key-value-pair object into a JSON string
# \param[in] kvp  a key-value-pair object
# \param[out] json_str string containing JSON result
uuKvp2JSON(*kvp, *json_str) {
	*json_str = "";
	msi_json_objops(*json_str, *kvp, "set");
}
