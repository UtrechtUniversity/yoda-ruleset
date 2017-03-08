testRule {
	iiCollectionMetadataList(*path, *prefix, *lst)
	writeLine("stdout", *lst);

	uuKvpList2JSON(*lst, *lst_str, *size);
	writeLine("stdout", *lst_str);
}
input *path="", *prefix=""
output ruleExecOut
