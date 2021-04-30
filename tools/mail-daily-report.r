mail_daily_report
{
    # Scan for all users with notifications.
    *ContInxOld = 1;
    msiAddSelectFieldToGenQuery("USER_NAME", "", *GenQInp);
    msiAddSelectFieldToGenQuery("META_USER_ATTR_NAME", "COUNT", *GenQInp);
    msiAddConditionToGenQuery("META_USER_ATTR_NAME", "like", "org_notification_%%", *GenQInp);

    msiExecGenQuery(*GenQInp, *GenQOut);

    msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

    while(*ContInxOld > 0) {
        foreach(*row in *GenQOut) {
            *to = *row.USER_NAME;
            *status="";
            *info="";

            rule_mail_notification_report(*to, *to, "55", *status, *info);


            *ContInxOld = *ContInxNew;
            if(*ContInxOld > 0) {
                msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
            }
        }
        msiCloseGenQuery(*GenQInp, *GenQOut);
    }
}

input null
output ruleExecOut
