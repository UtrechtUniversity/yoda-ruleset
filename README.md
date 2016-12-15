Institutions I-lab Rules and Policies for YoDa/iRODS
==========

NAME
----
irods-ruleset-ilab - Subset of rules and policies for iRODS based YoDa required for the yoda-portal-ilab-intake module 

DESCRIPTION
-----------
Yoda is configuration of an iRODS server for dataset management.
These rules are required on top of the rules-uu rules to use the YoDa Portal I-Lab Intake module

It consists of:
- Institutions I-lab specific rules and policies

Prerequisite: 
- [irods-ruleset-uu](https://github.com/UtrechtUniversity/irods-ruleset-uu)
- [MaastrichtUniversity/irods-microservices](https://github.com/MaastrichtUniversity/irods-microservices)
- Yoda rules require an iRODS 3.3.1+ server release.

INSTALLATION
-----------
1) On the iRODS server, become the iRODS user and navigate to ``/etc/irods``

2) Clone the repository.

3) Navigate to the directory this repository was cloned in

4) Checkout the target branch.

5) Use the make file to compile and install the rules: ``Make install``

6) Add the generated `rules-ii.re` (as well as the requisite `rules-uu.re`) to the `server_config.json` the _re_rulebase_set_, above `core` in `/etc/irods/server_config.json`:

```javascript
"re_rulebase_set": [
    {  "filename":  "rules-ii" },
    {  "filename":  "rules-uu" },
    { "filename": "core"}
]
```
    
7) Create a symlink from `job_iiCopySnapshotToVault.re` in the repository to `/etc/irods/job_iiCreateSnapshots.r`
    From the directory you cloned this repository to:
``````sh
$ ln -sv /etc/irods/job_iiCreateSnapshots.r job_iiCopySnapshotToVault.re
```
    
8) Using crontab -e, add the following cron job to a user with rodsadmin rights (this cronjob assumes the user has admin rights within iRODS and ``iinit`` has been executed after login):
```
* * * * * /bin/irule -F /etc/irods/job_iiCreateSnapshots.r >> $HOME/iRODS/server/log/job_iiCreateSnapshot.log 2> /dev/null
```
    
LICENSE
-------
This project is licensed under the GPLv3 license.

The full license can be found in [LICENSE](LICENSE).

AUTHORS
-------
- [Jan de Mooij](https://github.com/ajdemooij)
