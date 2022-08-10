mail_weekly_report
{
    # Any users subscribed to a weekly notification report?
    msiAddSelectFieldToGenQuery("USER_NAME", "COUNT", *GenQInpCount);
    msiAddConditionToGenQuery("META_USER_ATTR_NAME", "=", "org_settings_mail_notifications", *GenQInpCount);
    msiAddConditionToGenQuery("META_USER_ATTR_VALUE", "=", "WEEKLY", *GenQInpCount);

    msiExecGenQuery(*GenQInpCount, *GenQOutCount);

    *count = 0;
    foreach(*row in *GenQOutCount) {
        *count = int(*row.USER_NAME);
        break;
    }
    msiCloseGenQuery(*GenQInpCount, *GenQOutCount);

    if (*count==0) {
        writeLine("serverLog", "------- No weekly notification mail was sent out -----");
        writeLine("serverLog", "(No users were found subscribed to the weekly notification report)");
        succeed;
    }

    # Scan for all users with mail notifications enabled.
    *ContInxOld = 1;
    msiAddSelectFieldToGenQuery("USER_NAME", "", *GenQInp);
    msiAddConditionToGenQuery("META_USER_ATTR_NAME", "=", "org_settings_mail_notifications", *GenQInp);
    msiAddConditionToGenQuery("META_USER_ATTR_VALUE", "=", "WEEKLY", *GenQInp);

    msiExecGenQuery(*GenQInp, *GenQOut);
    msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

    *ContInxOld = *ContInxNew;
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
