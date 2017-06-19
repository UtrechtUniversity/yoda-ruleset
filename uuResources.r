# Resources and tiers 
#
# A tier designates a cost level of storage, i.e. resource.
# Some storage is more expensive than others. 

# A tier is added as metadata to a resources
# A resources can only have 1 tier.

# How does category link into all of this???


#
UUDEFAULTRESOURCETIER = 'Standard';
UUFRONTEND_SUCCESS = 'Success';
UUFRONTEND_UNRECOVERABLE = 'UNRECOVERABLE';



#  FRONT END FUNCTIONS TO BE CALLED FROM PHP WRAPPER

# /brief uuFrontEndGetResourceStatisticData
# /param[out] *data		-return actual requested data if applicable
# /param[out] *status		-return status to frontend 
# /param[out] *statusInfo	-return specific information regarding *status
# /param[in]  *resourceName
uuFrontEndGetResourceStatisticData(*resourceName, *data, *status, *statusInfo)
{

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin"){
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
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
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
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
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
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
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
        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
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

# /brief uuGetMonthlyCategoryStorageOverview() 
# FrontEnd function for retrieving storage overview for all
# /param[out] *result - JSON data with category overview
# /param[out] *status - 
# /param[out] *statusInfo
uuGetMonthlyCategoryStorageOverview(*result, *status, *statusInfo)
{
        *status = UUFRONTEND_SUCCESS;
        *statusInfo = '';

        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

	uuGetMonthlyStorageStatistics(*result, *status, *statusInfo)
}


#------------------------------------------ end of front end functions
#------------------------------------------ Start of supporting functions that probably exist already somewhere 


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

        # Initialize the actual metadata related to storage TODO: eet rid of the org_storage part
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
		if (*row.META_RESC_ATTR_VALUE == 'Standard') {
			*foundStandardTier = true;
		}
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

        *allResources;
}



# /brief uuGetMonthlyStorageStatistics()
# /param[out] *result - JSON representation of all found storage information on all categories 
# /param[out] *status
# /param[out] *statusInfo

# This function is directly dependant on the output of uuStoreMonthlyStorageStatistics.
# Current month is used to retrieve data.
# So this must be kept in line with the moment when new data is collected and stored!
uuGetMonthlyStorageStatistics(*result, *status, *statusInfo)
{
        # Really for the frontend but can be of use for this as well
        *status = 'Success';
        *statusInfo = '';

        *month = uuGetCurrentStatisticsMonth();
	
	  # Collection of all category, tier and storage values
        *listCatTierStorage = list();

        # All categories present        
        *listCategories = list();
        uuListCategories(*listCategories)

        # Get all existing tiers for initialisation purposes per category
        *allTiers = uuListResourceTiers(*result, *errorInfo);

        *metadataName = UUORGMETADATAPREFIX ++ 'storageDataMonth' ++ *month;
	
	# Aggregate (SUM) 'manually' to category/tier as all information is stored on grouplevel
        foreach (*categoryName in *listCategories) {
		msiString2KeyValPair("", *categoryTierStorage);

                # Set all tiers storage values to 0 for this category
                foreach (*tier in *allTiers) {
                        *categoryTierStorage."*tier" = '0';
                }

		foreach (*row in SELECT META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME 
				WHERE META_USER_ATTR_NAME = '*metadataName' 
				AND META_USER_ATTR_VALUE like '[\"*categoryName\",%%'  ) {
                	
			# resolve as JSON string holding an array ["category","tier","storage"]
			# Split on ',' where it is sure that a tier as well as a 
			*tierName = "";
			msi_json_arrayops( *row.META_USER_ATTR_VALUE, *tierName, "get", 1); #first position

                        *storage = "";
                        msi_json_arrayops( *row.META_USER_ATTR_VALUE, *storage, "get", 2);
        		
			*categoryTierStorage."*tierName" = str(int(*categoryTierStorage."*tierName") + int(*storage));
		}
		# Finished handling this category.
		# Add to kvp list
                foreach (*tier in *allTiers) {
                        msiString2KeyValPair("", *kvp);
                        *kvp.category = *categoryName;
                        *kvp.tier = *tier;
                        *kvp.storage = *categoryTierStorage."*tier";
                        *listCatTierStorage = cons(*kvp, *listCatTierStorage);
                }
	}

        uuKvpList2JSON(*listCatTierStorage, *result, *size);
}

# /param[in] *kvpList - list with all key-value pairs to be deleted
# /param[in] *objectName - description as known in dbs
# /param[in] *objectType - description as known within iRODS {-u, -C, etc}
uuRemoveKeyValuePairList(*kvpList, *objectName, *objectType, *status, *statusInfo)
{
	foreach (*kvp in *kvpList) {
                 *err = errormsg( msiRemoveKeyValuePairsFromObj(*kvp, *objectName, *objecType), *errmsg);
                 if (*err < 0) {
                         *status = 'ErrorDeletingMonthlyStorage';
                         *statusInfo = 'Error deleting metadata: *err - *errmsg';
                         succeed;
                 }
	}
}


# /brief uuStoreMonthlyStorageStatistics()
# For all categories known store all found storage data for each group belonging to those category
# Store as metadata on group level holding
# 1) category of group on probe date - this can change
# 2) tier
# 3) actual calculated storage for the group
uuStoreMonthlyStorageStatistics(*status, *statusInfo) 
{
	writeLine('serverLog', 'Start uuStoreMonthlyStorageStatistics');
	
	# Really for the frontend but can be of use for this as well
	*status = 'Success';
	*statusInfo = '';

	*month = uuGetCurrentStatisticsMonth();
        writeLine('serverLog', 'Month: *month ');

	*metadataName = UUORGMETADATAPREFIX ++ 'storageDataMonth' ++ *month;
	
	# First delete all previous data for this month-number
	*kvpList = list();
	foreach (*row in SELECT META_USER_ATTR_VALUE, USER_GROUP_NAME WHERE META_USER_ATTR_NAME = '*metadataName' ) {
	
                msiString2KeyValPair("", *kvp);
                msiAddKeyVal(*kvp, *metadataName, *row.META_USER_ATTR_VALUE);
		*kvpList = cons(*kvp, *kvpList);	
                 *err = errormsg( msiRemoveKeyValuePairsFromObj(*kvp, *row.USER_GROUP_NAME, "-u"), *errmsg);
                 if (*err < 0) {
	                 *status = 'ErrorDeletingMonthlyStorage';
        	         *statusInfo = 'Error deleting metadata: *err - *errmsg';
                         succeed;
                 }
	}
	# Problem here is that *objectName differs for vkp's. 
	# So it should be taken along in building the kvp list
	#uuRemoveKeyValuePairList(*kvpList, *objectName, *objectType, *status, *statusInfo);


        # zone is used to search in proper paths for storage
        *zone =  $rodsZoneClient;

        # All categories present        
        *listCategories = list();
        uuListCategories(*listCategories)

        # Get all existing tiers for initialisation purposes per category
        *allTiers = uuListResourceTiers(*result, *errorInfo);

        *kvpResourceTier = uuKvpResourceAndTiers();

         #per group find the storage amount for 
         # 1) dynamic storage and 
         # 2) vault
         *storageCalculationSteps = list("dynamic", "vault");

         # Per group two statements are required to gather all data 
         # 1) folder itself
         # 2) all subfolders of the folder

	# Step through all categories
        foreach (*categoryName in *listCategories) {
                *listGroups = list();
                uuListGroupsOnCategory(*categoryName, *listGroups);

                #per group find the storage amount for 
                # 1) dynamic storage and 
                # 2) vault
                foreach(*groupName in *listGroups ) {
                        msiString2KeyValPair("", *groupTierStorage);
                        foreach (*tier in *allTiers){ # initialize group tier storage
                                *groupTierStorage."*tier" = '0';
                        }

                        foreach (*step in *storageCalculationSteps) {
                                if (*step == 'dynamic') {
                                        *collName = '/*zone/home/'++ *groupName;
                                }
                                else { # vault sitation - strip groupname down to its basic name (research-)
                                        uuGetGroupNameForVault(*groupName, *groupNameVault);
                                        *collName = '/*zone/home/vault'++ *groupNameVault;
                                }
				
			        # Per group two statements are required to gather all data 
         			# 1) data in folder itself
         			# 2) data in all subfolders of the folder

				# 1) Collect all data in folder itself
                               	foreach (*row in SELECT SUM(DATA_SIZE), RESC_NAME WHERE COLL_NAME = '*collName') {
                                       	# This brings the total for dynamic storage of a group per RESOURCE

                                    	*thisResc = *row.RESC_NAME;
                                        *thisTier = *kvpResourceTier."*thisResc";

                                        # Totals on group level
                                        *newGroupSize = int(*groupTierStorage."*thisTier") + int(*row.DATA_SIZE);
                                        *groupTierStorage."*thisTier" = str(*newGroupSize);					
				}

				# 2) Collect all data in all subfolders of the folder
                                foreach (*row in SELECT SUM(DATA_SIZE), RESC_NAME WHERE COLL_NAME like '*collName/%%') {
                                        # This brings the total for dynamic storage of a group per RESOURCE

                                        *thisResc = *row.RESC_NAME;
                                        *thisTier = *kvpResourceTier."*thisResc";

                                        # Totals on group level
                                        *newGroupSize = int(*groupTierStorage."*thisTier") + int(*row.DATA_SIZE);
                                        *groupTierStorage."*thisTier" = str(*newGroupSize);
                                }



			}
                        # Group information complete.
			# Add it to dbs
                        foreach (*tier in *allTiers) {
                                msiString2KeyValPair("", *kvpGroupStorage);
                                *storage = *groupTierStorage."*tier";
                                *json_str = '["*categoryName","*tier","*storage"]';
                                *kvpGroupStorage."*metadataName" = *json_str;
                                *err = errormsg(msiAssociateKeyValuePairsToObj( *kvpGroupStorage, *groupName, "-u"), *errmsg);
				if (*err < 0) {
					*status = 'ErrorWritingMonthlyStorage';
					*statusInfo = 'Error adding metadata: *err - *errmsg';
					succeed;
				}
                        }
		}
	}
}

# /brief uuGetCurrentStatisticsMonth()
# returns the number of the month {'01',...'12'} that currently is the month reporting is about.
# In this case the breakpoint is set to halfway through a month.
# I.e. each statistics probe that is stored after the 15th, is related to the month after.
uuGetCurrentStatisticsMonth() 
{
        msiGetIcatTime(*timestamp, "icat");
        *month = int(timestrf(datetime(int(*timestamp)), "%m"));
	*day = int(timestrf(datetime(int(*timestamp)), "%d"));
	
	if (*day > 15) {
		*month = *month + 1;
		if (*month > 12) {
			*month = 1;
		}
	}
	# Format month as '01'-'12'
	*strMonth = str(*month);
	if (strlen(*strMonth)==1) {
		*strMonth = '0' ++ *strMonth;
	}
	*strMonth;
}

# /brief uuKvpResourceAndTiers()
# returns *kvp with resourceName as key and tierName as value 
# This way it is easy to use the name of a resource as an index and retrieve the corresponding tierName.
uuKvpResourceAndTiers() 
{
	*listResources = uuListResources();

	msiString2KeyValPair("", *kvp);

	foreach (*resource in *listResources) {
	
	# Because outerjoins are impossible in iRods and there is nog guarantee that all resources have org_m

		*resourceName = *resource.resourceName;
		*kvp."*resourceName" = 'Standard';	

		*sqlResource = *resource.resourceName;
                foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*sqlResource' AND META_RESC_ATTR_NAME = 'org_storageTierName' ) {
                        *kvp."*resourceName" = *row.META_RESC_ATTR_VALUE;
                }
	}

	*kvp;
}


# /brief Get a list of all known categories 
uuListCategories(*listCategories) 
{

        *listCategories = list();
        foreach (*row in SELECT META_USER_ATTR_VALUE
                WHERE  USER_TYPE            = 'rodsgroup'
                  AND  META_USER_ATTR_NAME  = 'category') {

                #writeLine('stdout', *row.META_USER_ATTR_VALUE);
		*listCategories = cons(*row.META_USER_ATTR_VALUE, *listCategories);
        }
}

# /brief List of groups 
# /param[in] *categoryName
# /param[out] *listGroups
uuListGroupsOnCategory(*categoryName, *listGroups) 
{
	*listGroups = list();
       foreach (
                *row in
                SELECT USER_NAME
                WHERE  USER_TYPE            = 'rodsgroup'
                  AND  META_USER_ATTR_NAME  = 'category'
                  AND  META_USER_ATTR_VALUE = '*categoryName'
        ) {

		*listGroups = cons(*row.USER_NAME, *listGroups);
        }
}

# /brief uuGetGroupNameForVault()  Get the base group name, stripped off of 'research-' etc
# /param[in] *groupName - full name of a group including 'research-' etc 
# /param[out] *groupBase
uuGetGroupNameForVault(*groupName, *groupBase) 
{
	*partsList = split(*groupName,'-');

         *count = 0;
         *groupBase = '';
         foreach (*part in *partsList) {
         	if (*count>0) {
                        *groupBase = *groupBase ++ '-' ++ *part;
                }
                *count = *count + 1;
         }
}

