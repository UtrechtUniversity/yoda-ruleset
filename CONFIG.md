iRODS system configuration for Yoda Youth Cohort
================================================
Manually ensure that the following settings are in place:

CORE.RE policies
----------------
set ACL policy to Strict
set trash policy to NOT use a trash

GENERAL ACCESS CONFIGURATION
----------------------------
Group public must have read access to /, /<zone>, /<zone>/home
so that webdav users can navigate it. 
e.g.: ichmod -M read public /

GROUP CONFIGURATION
-------------------
First install and configure the Yoda Portal Group Management module
This should create groups PRIV-xxxx and a collection /<zone>/group

Then for each Yoda Youth Cohort "studyabc"
------------------------------------------
Use the Yoda group Management portal to create 3 groups per study:
- grp-intake-studyabc
- grp-datamanager-studyabc
- grp-vault-studyabc

Important: make sure you do NOT add any members to the grp-vault-studyabc
because this would allow them to change vault data. The iRODS administrator
should remain (the only) group administrator of this group. 

Feel free to add users to the other two groups as per their role.
The intake group and the datamanager group can be managed by one of the
users e.g. a researcher, this does not have to be the iRODS administrator.

Manually add access rights to the groups as follows:
ichmod -M own rods /<zone>/home/grp-intake-studyabc
ichmod -M own rods /<zone>/home/grp-vault-studyabc
ichmod -M read grp-datamanager-studyabc /<zone>/home/grp-vault-studyabc 

NB: rods user needs own access to run the job that takes data from the
intake area to the vault area.

Optionally give datamanagers read access to the intake area of the study: 
ichmod -M read grp-datamanager-studyabc /<zone>/home/grp-intake-studyabc 


