# \file      uuResources.r
# \brief     Resources and tiers.
# \author    Harm de Raaff
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Resources and tiers
#
# A tier designates a cost level of storage, i.e. resource.
# Some storage is more expensive than others.

# A tier is added as metadata to a resources
# A resources can only have 1 tier.

# FRONT END FUNCTIONS TO BE CALLED FROM PHP WRAPPER

# \brief uuFrontEndGetResourceStatisticData
#
# \param[out] *data		-return actual requested data if applicable
# \param[out] *status		-return status to frontend
# \param[out] *statusInfo	-return specific information regarding *status
# \param[in]  *resourceName
#
uuFrontEndGetResourceStatisticData(*resourceName, *data, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

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
                        *status = 'UNRECOVERABLE';
                        *statusInfo = *errorInfo; # use the info from within the function
                }
		succeed;
	}

	uuKvp2JSON(*resourceData, *data);
}

# \brief Collect all groups current user is a member of. Read only groups count as well.
#
# \param[out] *data             -return actual requested data if applicable
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
#
uuFrontEndGetUserGroupsForStatistics(*data, *status, *statusInfo)
{
	*status = 'Success';
	*statusInfo = '';

	# include read only groups as well
	uuUserGetGroups(uuClientFullName, true, *allUserGroups);

	uuList2JSON(*allUserGroups, *data);
}

# \brief Return an overview that covers a year of storage statistics on a group
#        It returns a key value pair that is indexed with combination of month/tier data as a key
#
# \param[in]  *groupName	-Name of group storage statistics have to be gathered
# \param[in]  *currentMonth	-Central month that defines the start of the monthly list
# \param[out] *data             -return actual requested data if applicable
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
#
uuFrontEndGetYearStatisticsForGroup(*groupName, *currentMonth, *data, *status, *statusInfo)
{
	*status = 'Success';
	*statusInfo = '';


	uuGroupUserExists(*groupName, uuClientFullName, true, *membership);

	if (!*membership) {
		# check whether user is member of group
		*status = 'ERROR_NO_GROUP_MEMBER';
		*statusInfo = 'User is not a member of group ' ++ *groupName;
		succeed;
	}


	*listTierStorages = list();

	*counter = 0;


	# Collect storage for each month 1 year back

	while (*counter < 12) {
                *newMonth = int(*currentMonth) - *counter;
                if (*newMonth < 1) {
                        *newMonth = *newMonth + 12;
                }


		# Collect storages for tiers

		msiString2KeyValPair("", *kvpTierStorage);

		if (*newMonth<10) {
		        *metadataName = UUMETADATASTORAGEMONTH ++ '0' ++ str(*newMonth);
		}
		else {
			  *metadataName = UUMETADATASTORAGEMONTH ++ str(*newMonth);
		}

        	foreach (*row in SELECT META_USER_ATTR_VALUE, USER_NAME, USER_GROUP_NAME
        	                        WHERE META_USER_ATTR_NAME = '*metadataName'
					AND USER_NAME = '*groupName'
        	                               ) {

         	        # resolve as JSON string holding an array ["category","tier","storage"]
        	        *tierName = "";
                	msi_json_arrayops( *row.META_USER_ATTR_VALUE, *tierName, "get", 1);

                	*storage = "";
        	        msi_json_arrayops( *row.META_USER_ATTR_VALUE, *storage, "get", 2);

        	        #*categoryTierStorage."*tierName" = str(double(*categoryTierStorage."*tierName") + double(*storage));

	                # Add month to tiername as it seemd not possible to add a list as a value to a kvp
			*dblStorage = double(*storage);
			if (*dblStorage>0) {
				*monthTierName = "month=" ++ str(*newMonth) ++ "-tier=" ++ *tierName;

                		*kvpTierStorage."*monthTierName" = str(*dblStorage);

                		# Build list with storage amounts on tier level
                		*listTierStorages = cons(*kvpTierStorage, *listTierStorages);
			}

        	}

		*counter = *counter + 1;
        }
	uuKvpList2JSON(*listTierStorages, *data, *size);
}


# \brief List available resources and their tier & storage data
#
# \param[out] *data             -return actual requested data if applicable
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
#
uuFrontEndListResourcesAndStatisticData(*data, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        *allResourceData = uuListResourcesAndStatisticData(*result, *errorInfo);

        uuKvpList2JSON(*allResourceData, *data, *size);

        if (*size == 0 ) {  #TODO:  Mogelijkk nog verder differentieren
                *status = 'UNRECOVERABLE';
                *statusInfo = 'Impossible to convert data to JSON';
        }
}

# \brief List available resources and their tier & storage data
#
# \param[out] *data             -return actual requested data if applicable
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
#
uuFrontEndListResourceTiers(*data, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        *allResourceTiers = uuListResourceTiers(*result, *errorInfo);

	uuList2JSON(*allResourceTiers, *data);
}

# \brief sets (creates/updates) tier as metadata for given resource
#
# \param[out] *data             -return actual requested data if applicable
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
# \param[in]  *resourceName
# \param[in]  *tierName
#
uuFrontEndSetResourceTier(*resourceName, *tierName, *data, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

        uuSetResourceTier(*resourceName, *tierName, *result, *errorInfo);

        *data = ''; # N/A for this situation

        if (*result < 0) {
		if (*result == -1) {
        	        *status = 'NotExists';
               		*statusInfo = 'Resource does not exist';
        	}
        	else {
               		*status = 'UNRECOVERABLE';
               		*statusInfo = *errorInfo; # use the info from within the function
        	}
	}
}


# \brief uuGetMonthlyCategoryStorageOverview()
#
# FrontEnd function for retrieving storage overview for all
# \param[out] *result - JSON data with category overview
# \param[out] *status -
# \param[out] *statusInfo
#
uuGetMonthlyCategoryStorageOverview(*result, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

        uuGetUserType(uuClientFullName, *userType);
        if (*userType != "rodsadmin"){
                *status = 'NoPermissions';
                *statusInfo = 'Insufficient permissions';
                succeed;
        }

	uuGetMonthlyStorageStatistics(*result, *status, *statusInfo)
}


# \brief Front end function for retrieving storage overview for a datamanager.
#        Anyone can use this function - it will not yield anything if not a datamanager.
#        So no check for permissions is required.
#
# \param[out] *result - JSON data with category overview restricted to categories where user is part of a datamanager group
# \param[out] *status
# \param[out] *statusInfo
#
uuGetMonthlyCategoryStorageOverviewDatamanager(*result, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

	uuGetMonthlyStorageStatisticsDatamanager(*result, *status, *statusInfo);
}


# \brief Front end function for retrieving storage overview for a datamanager
#
# \param[out] *isDatamanager {'yes', 'no'}
# \param[out] *status
# \param[out] *statusInfo
#
uuUserIsDatamanager(*isDatamanager, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

	*isDatamanager = 'no';

        *user = uuClientFullName;
        # Get categories with datamanager groups
        foreach (
                *row in
                SELECT USER_NAME
                WHERE  USER_TYPE            = 'rodsgroup'
                        AND USER_NAME like 'datamanager-%%'
        ) {
                *datamanagerGroupName = *row.USER_NAME;
                uuGroupUserExists(*datamanagerGroupName, *user, true, *membership)
		if (*membership) {
			*isDatamanager = 'yes';
			succeed;
                }
        }
}


#------------------------------------------ end of front end functions
#------------------------------------------ Start of supporting functions that probably exist already somewhere


# \brief uuResourceExistst - check whether given resource actually exists
#
# \param[in] *resourceName
# \param[out] *exists
#
uuResourceExists(*resourceName, *exists)
{
        *exists = false;

        foreach(*row in SELECT RESC_ID, RESC_NAME WHERE RESC_NAME = '*resourceName') {
                *exists = true;
		succeed;
        }
}

#---------------------------------------- End of supporting functions that probably exist already somewhere

# \brief  uuGetResourceAndStatisticData
#
# \param[in] *resourceName
# \param[out] *result
# \param[out] *errorInfo
#
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
        *kvp.org_storage_tier = UUDEFAULTRESOURCETIER;

	*metaName = UURESOURCETIERATTRNAME;

        foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*resourceName' AND META_RESC_ATTR_NAME = '*metaName' ) {
        	*key = *row.META_RESC_ATTR_NAME;
                *kvp."*key" = *row.META_RESC_ATTR_VALUE;
        }

	*kvp;
}


# \brief uuSetResourceTier
#
# \param[in] 	*resourceName
# \param[in] 	*tierName
# \param[out] 	*result
# \param[out] 	*errorInfo
#
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


        # 2)Check whether tier- metadata exists for given resource based upon 'org_storage_tier' as meta attribute
        *metaFound = false;
	*metaName = UURESOURCETIERATTRNAME;
        foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*resourceName' AND META_RESC_ATTR_NAME='*metaName' ) {
                *metaFound = true;
                #writeLine("stdout",  *row.RESC_ID );
                #writeLine("stdout",  *row.RESC_NAME);
                #writeLine("stdout", *row.META_RESC_ATTR_NAME );
                #writeLine("stdout", *row.META_RESC_ATTR_VALUE);
                #writeLine("stdout", "------------------------------");
                #writeLine("stdout", *row.RESC_NAME);
        }

	writeLine('serverLog', 'Tier: ' ++  *tierName);

	msiString2KeyValPair("", *kvpResc);
        msiAddKeyVal(*kvpResc, *metaName, *tierName);

        if (!*metaFound ) {
                #writeLine("serverLog", "META NOT FOUND - INSERT");

                *err = msiAssociateKeyValuePairsToObj( *kvpResc, *resourceName, "-R");

		#writeLine("stdout", "Add KVP of RESC: *err ");
		if (*err!=0 ) {
			*result=-999;
			*errorInfo = 'Something went wrong adding tier metadata';
			succeed;
		}
        }
        else {
                #writeLine("serverLog", "META FOUND - UPDATE" );

		*err = msiSetKeyValuePairsToObj( *kvpResc, *resourceName, "-R");

		#writeLine("stdout", "UPDATE KVP of RESC: *err");
		if (*err!=0 ) {
                        *result=-999;
                        *errorInfo = 'Something went wrong updating tier metadata';
                        succeed;
                }
        }
}

# \brief List of  all resources and their tier/storage data (if present).
#        Tiers are only assigned to the resources that are allowed.
#        Therefore, no further restriction has to be added for the type of resource (which should be storage)
#
uuListResourceTiers(*result, *errorInfo)
{
        *result = 0;

	*foundStandardTier = false;
        *allRescTiers = list();

        # fetch tier information for all resources and filter duplicates
	*metaName = UURESOURCETIERATTRNAME;
        foreach(*row in SELECT META_RESC_ATTR_VALUE WHERE  META_RESC_ATTR_NAME = '*metaName' ) {
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

# \brief List of  all resources and their tier/storage data (if present).
#
uuListResourcesAndStatisticData(*result, *errorInfo)
{
	*result = 0;

        *allResources = uuListResources();
        *allRescStats = list();

	*metaName = UURESOURCETIERATTRNAME;
        foreach (*resource in *allResources) {
                msiString2KeyValPair("", *kvp);
                *kvp.resourceId = *resource.resourceId
                *kvp.resourceName = *resource.resourceName;

		# Initialize the actual metadata related to storage TODO: get rid of the org_storage part
		*kvp.org_storage_tier = UUDEFAULTRESOURCETIER;
                # fetch tier information in a seperate sql call as outerjoins are not possible
                *sqlResource = *resource.resourceName;
		foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*sqlResource' AND META_RESC_ATTR_NAME = '*metaName'  ) {
                       	*key = *row.META_RESC_ATTR_NAME;
                       	*kvp."*key" = *row.META_RESC_ATTR_VALUE;
		}
                *allRescStats = cons(*kvp, *allRescStats);
        }
        *allRescStats;
}

# \brief List of all existing resources TODO: exclude coordination resources.
#
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

# TODO: deze twee functies kunnen eigenlijk naar niveau dat wordt aangeroepen vanuit frontend
# \brief uuGetMonthlyStorageStatistics()
#
# \param[out] *result - JSON representation of all found storage information on all categories
# \param[out] *status
# \param[out] *statusInfo
#
uuGetMonthlyStorageStatistics(*result, *status, *statusInfo)
{
        *result = '[]';

        *status = 'Success';
        *statusInfo = '';

        # All categories present
        *listCategories = uuListCategories();

        #writeLine('stdout', *listCategories);
	#succeed;

	uuGetMonthlyCategoryStorageStatistics(*listCategories, *result, *status, *statusInfo);
}


# \brief uuGetMonthlyStorageStatisticsDatamanager()
#
# \param[out] *result - JSON representation of all found storage information on all categories
# \param[out] *status
# \param[out] *statusInfo
#
uuGetMonthlyStorageStatisticsDatamanager(*result, *status, *statusInfo)
{
	*result = '[]';

        *status = 'Success';
        *statusInfo = '';

	*listDMCategories = uuListCategoriesDatamanager();

	uuGetMonthlyCategoryStorageStatistics(*listDMCategories, *result, *status, *statusInfo);
}

# \brief This function is directly dependant on the output of uuStoreMonthlyStorageStatistics.
#        Current month is used to retrieve data.
#        So this must be kept in line with the moment when new data is collected and stored!
#
# \param[in] *listCategories - list of all categories that statistics need to be collected for
# \param[out] *result - JSON representation of all found storage information on all categories
# \param[out] *status
# \param[out] *statusInfo
#
uuGetMonthlyCategoryStorageStatistics(*listCategories, *result, *status, *statusInfo)
{
        # Really for the frontend but can be of use for this as well
        *status = 'Success';
        *statusInfo = '';

        *month = uuGetCurrentStatisticsMonth();

	  # Collection of all category, tier and storage values
        *listCatTierStorage = list();

        # Get all existing tiers for initialisation purposes per category
        *allTiers = uuListResourceTiers(*result, *errorInfo);

        *metadataName = UUMETADATASTORAGEMONTH ++ *month; #UUORGMETADATAPREFIX ++ 'storageDataMonth' ++ *month;

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
			*tierName = "";
			msi_json_arrayops( *row.META_USER_ATTR_VALUE, *tierName, "get", 1);

                        *storage = "";
                        msi_json_arrayops( *row.META_USER_ATTR_VALUE, *storage, "get", 2);

			*categoryTierStorage."*tierName" = str(double(*categoryTierStorage."*tierName") + double(*storage));
		}
		# Finished handling this category.
		# Add to kvp list
                foreach (*tier in *allTiers) {
			if (*categoryTierStorage."*tier"!='0') { #present only tears with actual data
                        	msiString2KeyValPair("", *kvp);
                        	*kvp.category = *categoryName;
                        	*kvp.tier = *tier;
                        	*kvp.storage = *categoryTierStorage."*tier";
                        	*listCatTierStorage = cons(*kvp, *listCatTierStorage);
			}
                }
	}

        uuKvpList2JSON(*listCatTierStorage, *result, *size);
}

# \brief
#
# \param[in] *kvpList - list with all key-value pairs to be deleted
# \param[in] *objectName - description as known in dbs
# \param[in] *objectType - description as known within iRODS {-u, -C, etc}
#
uuRemoveKeyValuePairList(*kvpList, *objectName, *objectType, *status, *statusInfo)
{
        *status = 'Success';
        *statusInfo = '';

	foreach (*kvp in *kvpList) {
                 *err = errormsg( msiRemoveKeyValuePairsFromObj(*kvp, *objectName, *objecType), *errmsg);
                 if (*err < 0) {
                         *status = 'ErrorDeletingMonthlyStorage';
                         *statusInfo = 'Error deleting metadata: *err - *errmsg';
                         succeed;
                 }
	}
}


# \brief For all categories known store all found storage data for each group belonging to those category.
#        Store as metadata on group level holding
#        1) category of group on probe date - this can change
#        2) tier
#        3) actual calculated storage for the group
#
uuStoreMonthlyStorageStatistics(*status, *statusInfo)
{
	writeLine('serverLog', 'Start uuStoreMonthlyStorageStatistics');

	# Really for the frontend but can be of use for this as well
	*status = 'Success';
	*statusInfo = '';

	*month = uuGetCurrentStatisticsMonth();
        writeLine('serverLog', 'Month: *month ');

	*metadataName = UUMETADATASTORAGEMONTH ++ *month;  #UUORGMETADATAPREFIX ++ 'storageDataMonth' ++ *month;

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

        #uuListCategories(*listCategories)

	*listCategories = uuListCategories();

        # Get all existing tiers for initialisation purposes per category
        *allTiers = uuListResourceTiers(*result, *errorInfo);

        *kvpResourceTier = uuKvpResourceAndTiers();

         #per group find the storage amount for
         # 1) dynamic storage and
         # 2) vault
         *storageCalculationSteps = list("dynamic", "vault");

	# 3) Furthermore each group's revision store has to be taken into account

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
				# 3) data from revisions of that group

				# 1) Collect all data in folder itself
                               	foreach (*row in SELECT SUM(DATA_SIZE), RESC_NAME WHERE COLL_NAME = '*collName') {
                                       	# This brings the total for dynamic storage of a group per RESOURCE

                                    	*thisResc = *row.RESC_NAME;
                                        *thisTier = *kvpResourceTier."*thisResc";

                                        # Totals on group level
                                        *newGroupSize = double(*groupTierStorage."*thisTier") + double(*row.DATA_SIZE);
                                        *groupTierStorage."*thisTier" = str(*newGroupSize);
				}

				# 2) Collect all data in all subfolders of the folder
                                foreach (*row in SELECT SUM(DATA_SIZE), RESC_NAME WHERE COLL_NAME like '*collName/%%') {
                                        # This brings the total for dynamic storage of a group per RESOURCE

                                        *thisResc = *row.RESC_NAME;
                                        *thisTier = *kvpResourceTier."*thisResc";

                                        # Totals on group level
                                        *newGroupSize = double(*groupTierStorage."*thisTier") + double(*row.DATA_SIZE);
                                        *groupTierStorage."*thisTier" = str(*newGroupSize);
                                }
			}

			# 3) Collect all data in revision folder of this group
			# This can be caught in a single statement as the group folder itself does not hold data
                        *revisionCollName = '/*zone' ++ UUREVISIONCOLLECTION ++ '/' ++ *groupName ++ '/%%';
                        foreach (*row in SELECT SUM(DATA_SIZE), RESC_NAME WHERE COLL_NAME like '*revisionCollName') {
                                # This brings the total for dynamic storage of a group per RESOURCE
                                *thisResc = *row.RESC_NAME;
                                *thisTier = *kvpResourceTier."*thisResc";

                                 # Totals on group level
                                 *newGroupSize = double(*groupTierStorage."*thisTier") + double(*row.DATA_SIZE);
                                 *groupTierStorage."*thisTier" = str(*newGroupSize);
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

# \brief Returns the number of the month {'01',...'12'} that currently is the month reporting is about.
#
uuGetCurrentStatisticsMonth()
{
        msiGetIcatTime(*timestamp, "icat");
        *month = int(timestrf(datetime(int(*timestamp)), "%m"));

# When you want to prevent changes to the statistics after a probe date use the code below
# I.e. each statistics probe that is stored after the 15th, is related to the month after.
#	*day = int(timestrf(datetime(int(*timestamp)), "%d"));

#	if (*day > 15) {
#		*month = *month + 1;
#		if (*month > 12) {
#			*month = 1;
#		}
#	}

	# Format month as '01'-'12'
	*strMonth = str(*month);
	if (strlen(*strMonth)==1) {
		*strMonth = '0' ++ *strMonth;
	}
	*strMonth;
}



# \brief Returns *kvp with resourceName as key and tierName as value.
#        This way it is easy to use the name of a resource as an index and retrieve the corresponding tierName.
uuKvpResourceAndTiers()
{
	*listResources = uuListResources();

	msiString2KeyValPair("", *kvp);

	*metaName = UURESOURCETIERATTRNAME;
	foreach (*resource in *listResources) {

	# Because outerjoins are impossible in iRods and there is nog guarantee that all resources have org_m

		*resourceName = *resource.resourceName;
		*kvp."*resourceName" = 'Standard';

		*sqlResource = *resource.resourceName;
                foreach(*row in SELECT RESC_ID, RESC_NAME, META_RESC_ATTR_NAME, META_RESC_ATTR_VALUE WHERE RESC_NAME='*sqlResource' AND META_RESC_ATTR_NAME = '*metaName' ) {
                        *kvp."*resourceName" = *row.META_RESC_ATTR_VALUE;
                }
	}

	*kvp;
}

# \brief Get a list of all known categories where current user is datamanager of.
#        Returns list of categories for this user as a datamanager.
#
uuListCategoriesDatamanager()
{
        *listCategories = list();
        *user = uuClientFullName;

        # Get categories current user is a datamanager of
        foreach (
                *row in
                SELECT USER_NAME
# \param[out] *status           -return status to frontend
# \param[out] *statusInfo       -return specific information regarding *status
                WHERE  USER_TYPE            = 'rodsgroup'
                        AND USER_NAME like 'datamanager-%%'
        ) {
                *datamanagerGroupName = *row.USER_NAME;
                uuGroupUserExists(*datamanagerGroupName, *user, true, *membership)
		if (*membership) {
			# datamanagerGroupName must be deciphered to get actual category (its prefixed with 'datamanager-'
			*partsCategories = split(*datamanagerGroupName,'-');
			*category = '';
			*counter = 0;
			foreach (*cat in *partsCategories) {
				if (*counter > 0) {
					if (*counter==1) {
						*category = *cat;
					}
					else {
						*category = *category ++ '-' ++ *cat;
					}
				}
				*counter = *counter + 1;
			}
			*listCategories = cons(*category, *listCategories);
		}
        }

	*listCategories;
}

# \brief Get a list of all known categories
#
uuListCategories()
{
        *listCategories = list();
        foreach (*row in SELECT META_USER_ATTR_VALUE
                WHERE  USER_TYPE            = 'rodsgroup'
                  AND  META_USER_ATTR_NAME  = 'category') {

                #writeLine('stdout', *row.META_USER_ATTR_VALUE);
		*listCategories = cons(*row.META_USER_ATTR_VALUE, *listCategories);
        }
	*listCategories;
}

# \brief List of groups.
#
# \param[in]  *categoryName
# \param[out] *listGroups
#
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

# \brief Get the base group name, stripped off of 'research-' etc.
#
# \param[in]  *groupName - full name of a group including 'research-' etc
# \param[out] *groupBase
#
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
