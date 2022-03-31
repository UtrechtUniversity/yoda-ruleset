mail_daily_report
{
    # Scan for all users with mail notifications enabled.
    *ContInxOld = 1;
    msiAddSelectFieldToGenQuery("USER_NAME", "", *GenQInp);
    msiAddConditionToGenQuery("META_USER_ATTR_NAME", "=", "org_settings_mail_notifications", *GenQInp);
    msiAddConditionToGenQuery("META_USER_ATTR_VALUE", "=", "DAILY", *GenQInp);

    msiExecGenQuery(*GenQInp, *GenQOut);
    msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

    while(*ContInxOld > 0) {
        foreach(*row in *GenQOut) {
            *user = *row.USER_NAME;
            foreach (
                *row2 in
                SELECT USER_NAME, COUNT(META_USER_ATTR_NAME)
                WHERE  USER_NAME = '*user'
                AND    META_USER_ATTR_NAME like 'org_notification_%%'
            ) {
                # Send mail notification if user has notifications.
                *to = *user;
                *notifications = str(*row2.META_USER_ATTR_NAME)
                *status="";
                *info="";
                rule_mail_notification_report(*to, *notifications, *status, *info);
            }

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
