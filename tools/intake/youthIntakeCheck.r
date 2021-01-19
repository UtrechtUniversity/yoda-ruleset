#Author Niek Bats

youthIntakeCheck {
        *intakeOrVault="intake"; #intake vault
        
        #non empty *wave, *experiment and *pseudocode
        if ((*wave != "") && (*experiment != "") && (*pseudocode != "")) then {
                foreach(*row in SELECT COLL_OWNER_ZONE) {
                        *zone=*row.COLL_OWNER_ZONE;

                        foreach(*row2 in SELECT COLL_NAME
                        WHERE COLL_NAME like '/*zone/home/grp-*intakeOrVault-%'
                        AND META_DATA_ATTR_NAME = 'wave'
                        AND META_DATA_ATTR_VALUE = *wave) {
                                *path=*row2.COLL_NAME;

                                foreach(*row3 in SELECT DATA_NAME
                                WHERE COLL_NAME = *path
                                AND META_DATA_ATTR_NAME = 'experiment_type'
                                AND META_DATA_ATTR_VALUE = *experiment) {
                                        *nameExtension=*row3.DATA_NAME;

                                        foreach(*row4 in SELECT DATA_SIZE
                                        WHERE DATA_NAME = *nameExtension
                                        AND COLL_NAME = *path
                                        AND META_DATA_ATTR_NAME = 'pseudocode'
                                        AND META_DATA_ATTR_VALUE = *pseudocode) {
                                                *size=*row4.DATA_SIZE;
                                                *name=trimr(*nameExtension, ".");
                                                *extension=triml(*nameExtension, *name);
                                        
                                                writeLine("stdout", "\"*path\";\"*name\";\"*extension\";\"*size\"");
                                        }
                                }
                        }
                }
        }
        
        #non empty *wave and *experiment
        else if ((*wave != "") && (*experiment != "")) then {
                foreach(*row in SELECT COLL_OWNER_ZONE) {
                        *zone=*row.COLL_OWNER_ZONE;
                        
                        foreach(*row2 in SELECT COLL_NAME
                        WHERE COLL_NAME like '/*zone/home/grp-*intakeOrVault-%'
                        AND META_DATA_ATTR_NAME = 'wave'
                        AND META_DATA_ATTR_VALUE = *wave) {
                                *path=*row2.COLL_NAME;
                                
                                foreach(*row3 in SELECT DATA_NAME, DATA_SIZE
                                WHERE COLL_NAME = *path
                                AND META_DATA_ATTR_NAME = 'experiment_type'
                                AND META_DATA_ATTR_VALUE = *experiment) {
                                        *nameExtension=*row3.DATA_NAME;
                                        *size=*row3.DATA_SIZE;
                                        *name=trimr(*nameExtension, ".");
                                        *extension=triml(*nameExtension, *name);
                                        
                                        writeLine("stdout", "\"*path\";\"*name\";\"*extension\";\"*size\"");
                                }
                        }
                }
        }
        
        #non empty wave pseudocode is empty
        else if (*wave != "" && *pseudocode == "") then {
                foreach(*row in SELECT COLL_OWNER_ZONE) {
                        *zone=*row.COLL_OWNER_ZONE;

                        foreach(*row2 in SELECT COLL_NAME, DATA_NAME, DATA_SIZE
                        WHERE COLL_NAME like '/*zone/home/grp-*intakeOrVault-%'
                        AND META_DATA_ATTR_NAME ='wave'
                        AND META_DATA_ATTR_VALUE = *wave) {
                                *path=*row2.COLL_NAME;
                                *nameExtension=*row2.DATA_NAME;
                                *size=*row2.DATA_SIZE;
                                *name=trimr(*nameExtension, ".");
                                *extension=triml(*nameExtension, *name);
                                
                                writeLine("stdout", "\"*path\";\"*name\";\"*extension\";\"*size\"");
                        }
                }
        }

        else {
                writeLine("stdout", "Invalid input");
        }
}

input *wave="", *experiment="", *pseudocode=""
output ruleExecOut