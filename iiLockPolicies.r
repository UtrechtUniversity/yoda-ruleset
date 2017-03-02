iiPreCollCreate(*path, *user) {
	writeLine("serverLog", "iiPreCollCreate(*path, *user)");
}

iiPreCollRename(*src, *dst, *user) {
	writeLine("serverLog", "iiPreCollRename(*src, *dst, *user)");
}

iiPreCollDelete(*path, *user) {
	writeLine("serverLog", "iiPreCollDelete(*path, *user)");
}

iiPreDataObjCreate(*path, *user) {
	writeLine("serverLog", "iiPreDataObjCreate(*path, *user)");
}

iiPreDataObjWrite(*path, *user) {
	writeLine("serverLog", "iiPreDataObjWrite(*path, *user)"); 
}

iiPreDataObjRename(*src, *dst, *user) {
	writeLine("serverLog", "iiPreDataObjRename(*src, *dst, *user)");
}

iiPreDataObjDelete(*path, *user) {
	writeLine("serverLog", "iiPreDataObjDelete(*path, *user)");
}

iiPreCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName) {
	writeLine("serverLog", "iiPreCopyMetadata(*option, *sourceItemType, *targetItemType, *sourceItemName, *targetItemName)");
}

iiPreModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit) {
	writeLine("serverLog", "iiPreModifyUserMetadata(*option, *itemType, *itemName, *attributeName, *attributeValue, *attributeUnit)");

}

iiPreModifyOrgMetadata(*option, *itemType, *itemName, *attributeName) {
	writeLine("serverLog", "iiPreModifyOrgMetadata(*option, *itemType, *itemName, *attributeName)");

}

iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue) {
	writeLine("serverLog", "iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue)");
	if (*option == "rm") {
		if (!iiIsStatusTransitionLegal(*attributeValue, UNPROTECTED)) {
			cut;
			msiOprDisallowed;
		}
	}
	if (*option == "add") {
		
		if (!iiIsStatusTransitionLegal(UNPROTECTED, *attributeValue)) {
			cut;
			msiOprDisallowed;
		}
	}
}

iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *newAttributeValue) {
	writeLine("serverLog", "iiPreModifyFolderStatus(*option, *path, *attributeName, *attributeValue, *newAttributeValue)");
}

