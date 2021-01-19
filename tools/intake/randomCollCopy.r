#Author Niek Bats
#Date: 2019-01-16

randomCollCopy {
 #changes YYYY-MM-DD.hh:mm:ss into seconds since epoch format
 msiHumanToSystemTime(*datefrom, *datefrom)
 msiHumanToSystemTime(*datetill, *datetill)
 
 foreach(*row in SELECT COLL_OWNER_ZONE) {
  *zone=*row.COLL_OWNER_ZONE;
  foreach(*row2 in SELECT COLL_NAME
                   WHERE COLL_NAME like '/*zone/home/grp-vault-%'
                   AND META_COLL_ATTR_NAME = 'wave'
                   AND META_COLL_ATTR_VALUE = *wave
                   # AND COLL_CREATE_TIME between *datefrom *datetill
                   #datefrom must be the same amount of digits as datetill
                   #wont be a problem if chosing times from yodas existence till future
                   ) {
   *name=*row2.COLL_NAME;
   foreach(*row3 in SELECT COLL_CREATE_TIME
                    WHERE COLL_NAME = *name
                    AND META_COLL_ATTR_NAME = 'experiment_type'
                    AND META_COLL_ATTR_VALUE = *experiment
                    ) {
     *collCreateTime=int(*row3.COLL_CREATE_TIME);
     writeLine("stdout", "*name");
	 
	 # test if already present in list - we do not want multiples.
   }
  }
 }
}

input *wave="", *experiment="", *datefrom="", *datetill=""
output ruleExecOut

