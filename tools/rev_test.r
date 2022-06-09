# \file
# \brief job
# \author Ton Smeele, Sietse Snel
# \copyright Copyright (c) 2015-2021, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#  This file can be executed manually or scheduled e.g. once a day.
#  It scans an intake collection for datasets and checks the sets, if no collection
#  is provided, it will scan a predefined list on intake groups (*groupList)
#
#  Prerequisite:  the irods user should have write access on the collection and its objects
#
#


uuYcRunRevisionBatch {
    *verbose='True';
    uuRevisionBatch(*verbose)

}

input *intakeRoot='dummy'
output ruleExecOut
