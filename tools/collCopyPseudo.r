#Author Harm de Raaff
#Date: 2019-01-16

collCopyPseudo {
    #changes YYYY-MM-DD.hh:mm:ss into seconds since epoch format
    msiHumanToSystemTime(*datefrom, *datefrom)
    msiHumanToSystemTime(*datetill, *datetill)

    # pseudocodes are passes as a comma-separated list. 
    *pseudoList = split(*pseudoCodes,',');

    foreach(*row in SELECT COLL_OWNER_ZONE) {
        *zone=*row.COLL_OWNER_ZONE;
        foreach(*pc in *pseudoList) {
            foreach(*row2 in SELECT COLL_NAME
                       WHERE COLL_NAME like '/*zone/home/grp-vault-%'
                       AND META_COLL_ATTR_NAME = 'pseudocode'
                       AND META_COLL_ATTR_VALUE = *pc
                       AND COLL_CREATE_TIME between *datefrom *datetill
                       #datefrom must be the same amount of digits as datetill
                       #wont be a problem if chosing times from yodas existence till future
                       ) {
                *name=*row2.COLL_NAME;
                writeLine('stdout', *name);
            }
        }
    }
}

input *pseudoCodes="", *datefrom="", *datetill=""
output ruleExecOut
