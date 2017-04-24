# Resources and tiers 
#
# A tier designates a cost level of storage, i.e. resource.
# Some storage is more expensive than others. 

# A tier is added as metadata to a resources
# A resources can only have 1 tier.

# How does category link into all of this???


#
UUDEFAULTRESOURCETIER = 'Standard';
UUFRONTEND_SUCCESS = 'SUCCESS';
UUFRONTEND_UNRECOVERABLE = 'UNRECOVERABLE';



#  FRONT END FUNCTIONS TO BE CALLED FROM PHP WRAPPER

# /brief uuFrontEndGetResourceStatisticData
# /param[out] *data		-return actual requested data if applicable
# /param[out] *status		-return status to frontend 
# /param[out] *statusInfo	-return specific information regarding *status
# /param[in]  *resourceName
uuFrontEndGetResourceStatisticData(*resourceName, *data, *status, *statusInfo)
{
	AmIAdministrator(*isAdministrator);
	if (!*isAdministrator){
		*status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
		succeed;
	}

        *resourceData = uuGetResourceAndStatisticData(*resourceName, *result, *errorInfo);
	# writeLine('stdout', *resourceData);
	
	if (*result < 0){
		if (*result == -1) {
                        *status = 'NotExists';
                        *statusInfo = 'Resource does not exist';
                }
                else {
                        *status = UUFRONTEND_UNRECOVERABLE;
                        *statusInfo = *errorInfo; # use the info from within the function
                }
		succeed;
	}

	uuKvp2JSON(*resourceData, *data);

        *status = UUFRONTEND_SUCCESS;
        *statusInfo = 'All went well!!';
}



# /brief uuFrontEndListResourceAndStatisticData - List available resources and their tier & storage data
# /param[out] *data             -return actual requested data if applicable
# /param[out] *status           -return status to frontend 
# /param[out] *statusInfo       -return specific information regarding *status
uuFrontEndListResourcesAndStatisticData(*data, *status, *statusInfo)
{
	AmIAdministrator(*isAdministrator);
        if (!*isAdministrator){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        *allResourceData = uuListResourcesAndStatisticData(*result, *errorInfo);

        uuKvpList2JSON(*allResourceData, *data, *size);

        *status = UUFRONTEND_SUCCESS;
        *statusInfo = 'All went well!!';

        if (*size == 0 ) {  #TODO:  Mogelijkk nog verder differentieren 
                *status = UUFRONTEND_UNRECOVERABLE;
                *statusInfo = 'Impossible to convert data to JSON';
        }
}


# /brief uuFrontEndListResourceTiers - List available resources and their tier & storage data
# /param[out] *data             -return actual requested data if applicable
# /param[out] *status           -return status to frontend 
# /param[out] *statusInfo       -return specific information regarding *status
uuFrontEndListResourceTiers(*data, *status, *statusInfo)
{
        AmIAdministrator(*isAdministrator);
        if (!*isAdministrator){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        *allResourceTiers = uuListResourceTiers(*result, *errorInfo);

	uuList2JSON(*allResourceTiers, *data);

        *status = UUFRONTEND_SUCCESS;
        *statusInfo = 'All went well!!';
}


# /brief uuFrontEndSetResourceTier - sets (creates/updates) tier as metadata for given resource
# /param[out] *data             -return actual requested data if applicable
# /param[out] *status           -return status to frontend 
# /param[out] *statusInfo       -return specific information regarding *status
# /param[in]  *resourceName
# /param[in]  *tierName
uuFrontEndSetResourceTier(*resourceName, *tierName, *data, *status, *statusInfo)
{
        AmIAdministrator(*isAdministrator);
        if (!*isAdministrator) {
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        uuSetResourceTier(*resourceName, *tierName, *result, *errorInfo);

        *data = ''; # N/A for this situation

        *status = UUFRONTEND_SUCCESS;
        *statusInfo = '';
	
        if (*result < 0) {
		if (*result == -1) {
        	        *status = 'NotExists';
               		*statusInfo = 'Resource does not exist'; 
        	}
        	else {
               		*status = UUFRONTEND_UNRECOVERABLE;
               		*statusInfo = *errorInfo; # use the info from within the function
        	}
	}
}

# /brief uuFrontEndSetResourceMonthlyStorage - sets (creates/updates) monthly storage as metadata for given resource 
# /param[out] *data             -return actual requested data if applicable
# /param[out] *status           -return status to frontend 
# /param[out] *statusInfo       -return specific information regarding *status
# /param[in]  *resourceName
# /param[in]  *month		{'01',...,'12'}	
# /param[in]  *usedStorage
uuFrontEndSetResourceMonthlyStorage(*resourceName, *month, *usedStorage, *data, *status, *statusInfo)
{
        AmIAdministrator(*isAdministrator);
        if (!*isAdministrator){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        uuSetResourceMonthlyStorage(*resourceName, *month, *usedStorage, *result, *errorInfo);

        *status = UUFRONTEND_SUCCESS;
        *statusInfo = '';

        if (*result < 0) {
                if (*result == -1) {
                        *status = 'NotExists';
                        *statusInfo = 'Resource does not exist';
                }
                else {
                        *status = UUFRONTEND_UNRECOVERABLE;
                        *statusInfo = *errorInfo; # use the info from within the function
                }
        }
}


#------------------------------------------ end of front end functions
#------------------------------------------ Start of supporting functions that probably exist already somewhere 
AmIAdministrator(*isAdministrator)
{	
	writeLine('stdout', $userNameClient);

	uuGetUserType($userNameClient, *userType);

	writeLine('stdout', *userType);
	
	*isAdministrator = false;
	if (*userType == 'rodsadmin') {
		*isAdministrator  = true;
	}
}

# /brief uuResourceExistst - check whether given resource actually exists
# /param[in] *resourceName
# /param[out] *exists
uuResourceExists(*resourceName, *exists)
{
        *exists = false;

        foreach(*row in SELECT RESC_ID, RESC_NAME WHERE RESC_NAME = '*resourceName') {
                *exists = true;
		succeed; 
        }
}

#---------------------------------------- End of supporting functions that probably exist already somewhere

# /brief  uuGetResourceAndStatisticData
# /param[in] *resourceName 
# /param[out] *result
# /param[out] *errorInfo
uuGetResourceAndStatisticData(*resourceName, *result, *errorInfo)
{
	*result = 0;
	
        # 1)First check whether resource actually exists
        uuResourceExists(*resourceName, *rescExists)
	
        if (!*rescExists) {
                *result = -1; # Resource does not exist.
		*errorInfo = 'Resource *resourceName does not exist';
                succeed;
        }
	
	# 2) start collecting the meta information (tier and storage data)
       
	msiString2KeyValPair("", *kvp);
	
        # *kvp.resourceId = *resource.resourceId - not known within this situation here.
        *kvp.resourceName = *resourceName;

        # Initialize the actual metadata related to storage TODO: get rid of the org_storage part
        *kvp.org_storageTierName = UUDEFAULTRESOURCETIER;

        *kvp.org_storageMonth01 = '0'; # storage used in TB
        *kvp.org_storageMonth02 = '0';
        *kvp.org_storageMonth03 = '0';
        *kvp.org_storageMonth04 = '0';
        *kvp.org_storageMonth05 = '0';
        *kvp.org_storageMonth06 = '0';
        *kvp.org_storageMonth07 = '0';
        *kvp.org_storageMonth08 = '0';
        *kvp.org_storageMonth09 = '0';
        *kvp.org_storageMonth10 = '0';
        *kvp.org_storageMonth11 = '0';
        *kvp.org_storageMonth12 = '0';

        foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*resourceName' AND META_RESC_ATTR_NAME like 'org_storage%%' ) {
        	*key = *row.META_RESC_ATTR_NAME;
                *kvp."*key" = *row.META_RESC_ATTR_VALUE;
        }
	
	*kvp;
}


# /brief uuSetResourceMonthlyStorage
# /param[in]    *resourceName
# /param[in]    *month {'01'...'12'}
# /param[out]   *usedStorage
# /param[out]	*result
# /param[out]   *errorInfo
uuSetResourceMonthlyStorage(*resourceName, *month, *usedStorage, *result, *errorInfo)
{
        *result = 0;

        # 1)First check whether resource actually exists
	uuResourceExists(*resourceName, *rescExists)
	
        if (!*rescExists) {
                *result = -1; # Resource does not exist
		*errorInfo = 'Resource *resourceName does not exist';
                succeed;
        }


        # 2)Check whether storage metadata exists for given resource for this month 

        *metaFound = false;
        *metaName = UUORGMETADATAPREFIX ++ 'storageMonth' ++ *month ;
        foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*resourceName' AND META_RESC_ATTR_NAME='*metaName' ) {
                *metaFound = true;
        }

        msiString2KeyValPair("", *kvpResc);
        msiAddKeyVal(*kvpResc, *metaName, *usedStorage);

        if (!*metaFound ) {
                #writeLine("stdout", "META NOT FOUND - INSERT");

                *err = msiAssociateKeyValuePairsToObj( *kvpResc, *resourceName, "-R");

                #writeLine("stdout", "Add KVP of RESC: *err ");
                if (*err!=0 ) {
                        *result=-999;
                        *errorInfo = 'Something went wrong adding tier metadata';
                        succeed;
                }
        }
        else {
                #writeLine("stdout", "META FOUND - UPDATE" );

                *err = msiSetKeyValuePairsToObj( *kvpResc, *resourceName, "-R");

                #writeLine("stdout", "UPDATE KVP of RESC: *err");
                if (*err!=0 ) {
                        *result=-999;
                        *errorInfo = 'Something went wrong updating tier metadata';
                        succeed;
                }
        }
}

# /brief uuSetResourceTier
# /param[in] 	*resourceName
# /param[in] 	*tierName
# /param[out] 	*result
# /param[out] 	*errorInfo
uuSetResourceTier(*resourceName, *tierName, *result, *errorInfo)
{	
	*result = 0;
        
	# 1)First check whether resource actually exists
        uuResourceExists(*resourceName, *rescExists)

        if (!*rescExists) {
                *result = -1; # Resource does not exist.
		*errorInfo = 'Resource *resourceName does not exist';
                succeed;
        }


        # 2)Check whether tier- metadata exists for given resource based upon 'org_storageTierName' as meta attribute
        *metaFound = false;
	*metaName = UUORGMETADATAPREFIX ++ 'storageTierName';
        foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*resourceName' AND META_RESC_ATTR_NAME='*metaName' ) {
                *metaFound = true;
                writeLine("stdout",  *row.RESC_ID );
                writeLine("stdout",  *row.RESC_NAME);
                writeLine("stdout", *row.META_RESC_ATTR_NAME );
                writeLine("stdout", *row.META_RESC_ATTR_VALUE);
                writeLine("stdout", "------------------------------");
                #writeLine("stdout", *row.RESC_NAME);
        }
	
	# writeLine('stdout', *tierName);

	msiString2KeyValPair("", *kvpResc);
        msiAddKeyVal(*kvpResc, *metaName, *tierName);

        if (!*metaFound ) {
                #writeLine("stdout", "META NOT FOUND - INSERT");

                *err = msiAssociateKeyValuePairsToObj( *kvpResc, *resourceName, "-R");
                
		#writeLine("stdout", "Add KVP of RESC: *err ");
		if (*err!=0 ) {
			*result=-999;
			*errorInfo = 'Something went wrong adding tier metadata';
			succeed;
		}
        }
        else {
                #writeLine("stdout", "META FOUND - UPDATE" );
                
		*err = msiSetKeyValuePairsToObj( *kvpResc, *resourceName, "-R");
                
		#writeLine("stdout", "UPDATE KVP of RESC: *err");
		if (*err!=0 ) {
                        *result=-999;
                        *errorInfo = 'Something went wrong updating tier metadata';
                        succeed;
                }
        }
}

# /brief uuResourcesAndStatisticData  - List of  all resources and their tier/storage data (if present)

# Tiers are only assigned to the resources that are allowed. 
# Therefore, no further restriction has to be added for the type of resource (which should be storage)
uuListResourceTiers(*result, *errorInfo)
{
        *result = 0;

	*foundStandardTier = false;
        *allRescTiers = list();
	
        # fetch tier information for all resources and filter duplicates
        foreach(*row in SELECT META_RESC_ATTR_VALUE WHERE  META_RESC_ATTR_NAME = 'org_storageTierName' ) {
        	# writeLine('stdout', *row.META_RESC_ATTR_VALUE);
                *allRescTiers = cons(*row.META_RESC_ATTR_VALUE, *allRescTiers);
        }

	if (!*foundStandardTier) { # Add standard tier if not found in database
		*allRescTiers = cons('Standard', *allRescTiers);
	}

        *allRescTiers;
}


# -----------------------------------------------------------------------------------
# /brief uuResourcesAndStatisticData  - List of  all resources and their tier/storage data (if present)
uuListResourcesAndStatisticData(*result, *errorInfo)
{
	*result = 0;		

        *allResources = uuListResources();
        *allRescStats = list();

        foreach (*resource in *allResources) {
                msiString2KeyValPair("", *kvp);
                *kvp.resourceId = *resource.resourceId
                *kvp.resourceName = *resource.resourceName;
                
		# Initialize the actual metadata related to storage TODO: get rid of the org_storage part
		*kvp.org_storageTierName = UUDEFAULTRESOURCETIER;
                
                *kvp.org_storageMonth01 = '0'; # storage used in TB
                *kvp.org_storageMonth02 = '0';
                *kvp.org_storageMonth03 = '0';
                *kvp.org_storageMonth04 = '0';
                *kvp.org_storageMonth05 = '0';
                *kvp.org_storageMonth06 = '0';
                *kvp.org_storageMonth07 = '0';
                *kvp.org_storageMonth08 = '0';
                *kvp.org_storageMonth09 = '0';
                *kvp.org_storageMonth10 = '0';
                *kvp.org_storageMonth11 = '0';
                *kvp.org_storageMonth12 = '0';

                # fetch tier information in a seperate sql call as outerjoins are not possible
                *sqlResource = *resource.resourceName;
		foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*sqlResource' AND META_RESC_ATTR_NAME like 'org_storage%%' ) {
                       	*key = *row.META_RESC_ATTR_NAME;
			#writeLine('stdout', *key);
                       	*kvp."*key" = *row.META_RESC_ATTR_VALUE;
		}
                *allRescStats = cons(*kvp, *allRescStats);
        }
        *allRescStats;
}


# /brief uuListResources - List of all existing resources TODO: exclude coordination resources
uuListResources()
{
        *allResources = list();

        foreach(*row in SELECT RESC_ID, RESC_NAME ) {
                msiString2KeyValPair("", *kvp);
                *kvp.resourceId = *row.RESC_ID;
                *kvp.resourceName = *row.RESC_NAME;
		# writeLine('stdout', 'name: ' ++ *kvp.resourceName);
                *allResources = cons(*kvp, *allResources);
        }
        #writeLine('stdout', *allResources);

        *allResources;
}


