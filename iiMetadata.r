# \file      iiMetadata.r
# \brief     This file contains rules related to metadata to a dataset.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2019, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# \brief Validate XML against XSD schema.
#
# \param[in] metadataXmlPath path of the metadata XML file that needs to be converted
# \param[out] xsdPath        path of the vault XSD to use for validation
# \param[out] err            Zero is valid XML, negative is microservice error, positive is invalid XML
#
iiValidateXml(*metadataXmlPath, *xsdPath, *invalid, *msg) {
    *invalid = 0;
    *err = errormsg(msiXmlDocSchemaValidate(*metadataXmlPath, *xsdPath, *statusBuf), *msg);
    if (*err < 0) {
            *invalid = 1;
    } else {
            # Output in status buffer means XML is not valid.
            msiBytesBufToStr(*statusBuf, *statusStr);
            *len = strlen(*statusStr);
            if (*len == 0) {
                    #DEBUG writeLine("serverLog", "iiValidateXML: *metadataXmlPath validates");
            } else {
                    #DEBUG writeLine("serverLog", "iiValidateXML: *metadataXmlPath - *statusStr");
                    *invalid = 1;
        }
}

# \brief Remove the User AVU's from the irods AVU store.
#
# \param[in] coll	    Collection to scrub of user metadata
# \param[in] prefix	    prefix of metadata to remov
#
iiRemoveAVUs(*coll, *prefix) {
	#DEBUG writeLine("serverLog", "iiRemoveAVUs: Remove all AVU's from *coll prefixed with *prefix");
	msiString2KeyValPair("", *kvp);
	*prefix = *prefix ++ "%";

	*duplicates = list();
	*prev = "";
	foreach(*row in SELECT order_asc(META_COLL_ATTR_NAME), META_COLL_ATTR_VALUE WHERE COLL_NAME = *coll AND META_COLL_ATTR_NAME like *prefix) {
		*attr = *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		if (*attr == *prev) {
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Duplicate attribute " ++ *attr);
		       *duplicates = cons((*attr, *val), *duplicates);
		} else {
			msiAddKeyVal(*kvp, *attr, *val);
			#DEBUG writeLine("serverLog", "iiRemoveAVUs: Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
			*prev = *attr;
		}
	}

	msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");

	foreach(*pair in *duplicates) {

		(*attr, *val) = *pair;
		#DEBUG writeLine("serverLog", "iiRemoveUserAVUs: Duplicate key Attribute=\"*attr\", Value=\"*val\" from *coll will be removed");
		msiString2KeyValPair("", *kvp);
		msiAddKeyVal(*kvp, *attr, *val);
		msiRemoveKeyValuePairsFromObj(*kvp, *coll, "-C");
	}
}

# \brief Ingest user metadata from XML preprocessed with an XSLT.
#
# \param[in] metadataxmlpath	path of metadataxml to ingest
# \param[in] xslpath		path of XSL stylesheet
#
iiImportMetadataFromXML (*metadataxmlpath, *xslpath) {
	#DEBUG writeLine("serverLog", "iiImportMetadataFromXML: calling msiXstlApply '*xslpath' '*metadataxmlpath'");
	# apply xsl stylesheet to metadataxml
	msiXsltApply(*xslpath, *metadataxmlpath, *buf);
	#DEBUG writeBytesBuf("serverLog", *buf);

	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	#DEBUG writeLine("serverLog", "iiImportMetdataFromXML: Calling msiLoadMetadataFromXml");
	*err = errormsg(msiLoadMetadataFromXml(*metadataxml_coll, *buf), *msg);
	if (*err < 0) {
		writeLine("serverLog", "iiImportMetadataFromXML: *err - *msg ");
	} else {
		writeLine("serverLog", "iiImportMetadataFromXML: Succesfully loaded metadata from *metadataxmlpath");
	}
}

# \brief Perform a vault ingest as rodsadmin.
#
iiAdminVaultIngest() {
	msiExecCmd("admin-vaultingest.sh", uuClientFullName, "", "", 0, *out);
}

# \brief iiLogicalPathFromPhysicalPath
#
# \param[in]  physicalPath
# \param[out] logicalPath
# \param[in]  zone
#
iiLogicalPathFromPhysicalPath(*physicalPath, *logicalPath, *zone) {
	*lst = split(*physicalPath, "/");
	# find the start of the part of the path that corresponds to the part identical to the logical_path. This starts at /home/
	uuListIndexOf(*lst, "home", *idx);
	if (*idx < 0) {
		writeLine("serverLog","iiLogicalPathFromPhysicalPath: Could not find home in *physicalPath. This means this file came outside a user visible path and thus this rule should not have been invoked") ;
		fail;
	}
	# skip to the part of the path starting from ../home/..
	for( *el = 0; *el < *idx; *el = *el + 1) {
		*lst = tl(*lst);
	}
	# Prepend with the zone and rejoin to a logical path
	*lst	= cons(*zone, *lst);
	uuJoin("/", *lst, *logicalPath);
	*logicalPath = "/" ++ *logicalPath;
	#DEBUG writeLine("serverLog", "iiLogicalPathFromPhysicalPath: *physicalPath => *logicalPath");
}

# \brief iiGetLatestVaultMetadataXml
#
# \param[in] vaultPackage
# \param[out] metadataXmlPath
#
iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath, *metadataXmlSize) {
	uuChopFileExtension(IIMETADATAXMLNAME, *baseName, *extension);
	*dataNameQuery = "%*baseName[%].*extension";
	*dataName = "";
	*metadataXmlPath = "";
	foreach (*row in SELECT DATA_NAME, DATA_SIZE WHERE COLL_NAME = *vaultPackage AND DATA_NAME like *dataNameQuery) {
		if (*dataName == "" || (*dataName < *row.DATA_NAME && strlen(*dataName) <= strlen(*row.DATA_NAME))) {
			*dataName = *row.DATA_NAME;
			*metadataXmlPath = *vaultPackage ++ "/" ++ *dataName;
			*metadataXmlSize = int(*row.DATA_SIZE);
		}
	}
}

# \brief iiGetLatestVaultMetadataJson
#
# \param[in] vaultPackage
# \param[out] metadataJsonPath
#
iiGetLatestVaultMetadataJson(*vaultPackage, *metadataJsonPath, *metadataJsonSize) {
	uuChopFileExtension(IIJSONMETADATA, *baseName, *extension);
	*dataNameQuery = "%*baseName[%].*extension";
	*dataName = "";
	*metadataJsonPath = "";
	foreach (*row in SELECT DATA_NAME, DATA_SIZE WHERE COLL_NAME = *vaultPackage AND DATA_NAME like *dataNameQuery) {
		if (*dataName == "" || (*dataName < *row.DATA_NAME && strlen(*dataName) <= strlen(*row.DATA_NAME))) {
			*dataName = *row.DATA_NAME;
			*metadataJsonPath = *vaultPackage ++ "/" ++ *dataName;
			*metadataJsonSize = int(*row.DATA_SIZE);
		}
	}
}
