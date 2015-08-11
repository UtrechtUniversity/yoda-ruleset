#!/usr/bin/env python

"""
Yoda privileged services - Group management

On errors (lack of privileges, icommand failures or python errors),
the STDERR output of this script will start with 'Error: ' and contain a
technical error message that is to be written to a log by the calling program.

If an error occurs, the STDOUT output of this program will contain a user-friendly
error message and is to be shown directly to the user.

This script should always exit with exit code 0, see fail().

Invocation examples:

- Creating a new group:

    group-manager.py add GROUP_NAME

- Adding a user to a group (user is created if they do not yet exist):

    group-manager.py add-user GROUP_NAME USER_NAME

- Removing a user from a group:

    group-manager.py remove-user GROUP_NAME USER_NAME

- Changing group properties:

    group-manager.py set GROUP_NAME (category|subcategory|description|managers) VALUE

Note: The managers group property must be given as a semicolon-separated list,
      any current managers not in the supplied list will be demoted.


License information follows:

Copyright (c) 2015, Utrecht University. All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function

__author__  = 'Chris Smeele'
__version__ = '0.1'

import json
import sys
import os
import subprocess
import tempfile
import random

class GmException(Exception):
    """
    General GroupManager exception.

    Contains both a technical error message to be written to logs and a
    user-friendly message.
    """
    def __init__(self, errorMessage, userFeedback):
        super(Exception, self).__init__(errorMessage, userFeedback)

class GroupManager(object):
    """
    Group manager class containing all python functions related to group management.

    All errors should raise a GmException.
    Lack of privileges is also signaled using a GmException, with a proper bit of user feedback.
    """
    def icommand(self, cmd, args, stdin=None, critical=True):
        """
        Run an icommand and return the results

        param cmd:      Any executable path or name (when in $PATH)
        param args:     A list of arguments to feed to the command
        param stdin:    If not None, input to feed to the command through subprocess.communicate()
        param critical: If False, does not throw an exception when the command's exit code is
                        non-zero

        returns: If critical: (stdout, stderr), else: (stdout, stderr, exitCode)
        """
        args.insert(0, cmd)

        proc = subprocess.Popen(
            args,
            stdin  = subprocess.PIPE,
            stderr = subprocess.PIPE,
            stdout = subprocess.PIPE,
            env    = self.env
        )

        if stdin is not None:
            out, err = proc.communicate(stdin)
        else:
            out, err = proc.communicate()

        status = proc.wait()

        if critical and status != 0:
            raise GmException(
                  cmd + ' returned ' + str(status) + ', output follows:'
                + '\nICOMMAND STDOUT:\n' + out
                + '\nICOMMAND STDERR:\n' + err,
                'Unknown error'
            )

        return (out, err) if critical else (out, err, status)

    def rule(self, ruleName, inputParams, outputTypes):
        """
        Call a rule with irule and return output parameters.

        Only string-type input parameters are supported.

        Output parameter types must be one of the following:
        - string
        - int
        - bool
        - list

        param ruleName:     The name of the rule to call
        param inputParams:  A list of input parameter values
        param outputTypes:  A list of output parameter types

        returns: A tuple of the given output parameters
        """

        tempRuleName = 'rule' + ('%04d' % random.randint(1, 9999))

        # Use a string that should not occur in the rule's output parameters.
        outputBoundary = '%032x' % random.getrandbits(128)
        listBoundary   = '%032x' % random.getrandbits(128)

        with tempfile.NamedTemporaryFile(suffix = '.r') as ruleFile:
            ruleFile.write(tempRuleName + '() {\n')
            ruleFile.write(
                '\t'
                + ruleName + '('
                    + ', '.join([
                        ', '.join(['"' + val.replace('"', '\\"') + '"' for val in inputParams]),
                        ', '.join(['*_outParam' + str(i) for i, paramType in enumerate(outputTypes)])
                      ])
                + ');\n'
            )

            ruleFile.write('\t*_outputBoundary = "' + outputBoundary + '";\n')

            if 'list' in outputTypes:
                ruleFile.write('\t*_listBoundary   = "' + listBoundary + '";\n')

            ruleFile.write('\t*_output = "";\n')

            for i, paramType in enumerate(outputTypes):
                paramCode = ''
                paramName = '*_outParam' + str(i)

                if i > 0:
                    paramCode += '\t*_output = *_output ++ *_outputBoundary;\n'

                if   paramType in ('string', 'int'):
                    paramCode += '\t*_output = *_output ++ ' + paramName + ';\n'

                elif paramType == 'bool':
                    paramCode += '\t*_output = *_output ++ (if ' + paramName + ' then "true" else "false");\n'

                elif paramType == 'list':
                    paramCode += '\t*_i = 0;\n'
                    paramCode += '\tforeach(*_item in ' + paramName + ') {\n'
                    paramCode += '\t\tif (*_i > 0) {\n'
                    paramCode += '\t\t\t*_output = *_output ++ *_listBoundary;\n'
                    paramCode += '\t\t}\n'
                    paramCode += '\t\t*_output = *_output ++ *_item;\n'
                    paramCode += '\t\t*_i = *_i + 1;\n'
                    paramCode += '\t}\n'

                else:
                    raise GmException('Invalid output parameter type', 'An internal error occurred. Please contact a Yoda administrator if problems persist.')

                ruleFile.write(paramCode)

            ruleFile.write('\twriteLine("stdout", *_output);\n')

            ruleFile.write('}\n')
            ruleFile.write('input *ruleName="' + tempRuleName + '"\n')
            ruleFile.write('output ruleExecOut\n')
            ruleFile.flush()

            (out, err) = self.icommand('irule', ['-F', ruleFile.name])

            # Extract output parameter values from the rule output string and
            # convert them to the matching python type.
            return [
                (
                    strValue                     if paramType == 'string' else
                    int(strValue)                if paramType == 'int'    else
                    (strValue == 'true')         if paramType == 'bool'   else
                    strValue.split(listBoundary) if paramType == 'list'   else
                    None
                )
                    for paramType, strValue
                        in zip(outputTypes, out.rstrip('\n\r').split(outputBoundary))
            ]

    def requireAccess(self, actionDescription, checkName, *args):
        """
        Check if the client passes the given policy check.

        Raises an exception with a descriptive error message when access is denied
        by the check rule.

        param actionDescription: A human readable short description of the action,
                                 to be used in an error message prefixed with
                                 'Could not ' ...
        param checkName:         The name of the check to execute. Will be prefixed with
                                 'uuGroupPolicyCan'.
        param *args:             A list of arguments to the check function

        returns: Nothing. The function returning indicates that access is granted.
        """
        ruleName = 'uuGroupPolicyCan' + checkName
        args = (self.clientUsername,) + args

        (allowed, reason) = self.rule(ruleName, args, ['bool', 'string'])

        if not allowed:
            raise GmException(
                'Action disallowed by policy check \'' + ruleName + '\'',
                'Could not ' + actionDescription + ': ' + reason
            )

    # Group manager actions {{{

    def groupAdd(self, groupName):
        """
        Create a new Yoda group.

        param groupName: The name of the group to create
        """
        self.requireAccess('create group', 'GroupAdd', groupName)

        self.icommand('iadmin', ['mkgroup', groupName])

        groupDir = '/%s/group/%s' % (self.zone, groupName)

        try:
            self.icommand('imkdir', [groupDir], critical = False)
            self.icommand('iadmin', ['atg', groupName, self.clientUsername])

            self.icommand('imeta',  ['set', '-C', groupDir, 'category',      'uncategorized'    ])
            self.icommand('imeta',  ['set', '-C', groupDir, 'subcategory',   'uncategorized'    ])
            self.icommand('imeta',  ['set', '-C', groupDir, 'description',   '.'                ])
            self.icommand('imeta',  ['set', '-C', groupDir, 'administrator', self.clientUsername])

        except:
            # If any of the above commands failed, try to revert group creation.
            self.icommand('irm',    ['-r',      groupDir ], critical = False)
            self.icommand('iadmin', ['rmgroup', groupName], critical = False)
            raise

    def groupRemove(self, groupName):
        """
        Remove a group.

        param groupName: The name of the group to delete
        """
        self.requireAccess('remove group', 'GroupRemove', groupName)
        self.icommand('iadmin', ['rmgroup', groupName])

        groupDir = '/%s/group/%s' % (self.zone, groupName)
        self.icommand('irm', ['-r', groupDir])

    def groupUserAdd(self, groupName, userName):
        """
        Add a user to a group.

        The user will be created if they do not yet exist in iRODS, if the
        policy check functions allow it.

        param groupName: The name of the group
        param userName:  The name of the user to add to the group
        """
        self.requireAccess('add user to group', 'GroupUserAdd', groupName, userName)

        (userExists,) = self.rule('uuUserExists', [userName], ['bool'])
        if not userExists:
            self.icommand('iadmin', ['mkuser', userName, 'rodsuser'])

        try:
            self.icommand('iadmin', ['atg', groupName, userName])

        except:
            if userExists == 'false':
                # We created a new user but could not add them to the group.
                # Remove the orphan user.
                self.icommand('iadmin', ['rmuser', userName], critical = False)
            raise

    def groupUserRemove(self, groupName, userName):
        """
        Remove a user from a group.

        param groupName: The name of the group
        param userName:  The name of the user to remove from the group
        """
        self.requireAccess('remove user from group', 'GroupUserRemove', groupName, userName)

        (isManager,) = self.rule('uuGroupUserIsManager', [groupName, userName], ['bool'])
        if isManager:
            # We need to remove the user from the manager list first.
            # We bypass the groupModify policy check here, since being allowed to remove a
            # user from a group implies that we also have the right to demote them.
            groupDir = '/%s/group/%s' % (self.zone, groupName)
            self.icommand('imeta',  ['rm',  '-C', groupDir, 'administrator', userName])

        self.icommand('iadmin', ['rfg', groupName, userName])

    def groupModify(self, groupName, propertyName, value):
        """
        Modify group properties.

        propertyName must be one of 'category', 'subcategory', 'description', and 'managers'.

        param groupName:    The name of the group
        param propertyName: The property to modify
        param value:        The new property value
        """
        self.requireAccess('change group properties', 'GroupModify', groupName, propertyName, value)

        groupDir = '/%s/group/%s' % (self.zone, groupName)

        if propertyName == 'managers':
            newManagers     = set(value.split(';'))
            currentManagers = set(self.rule('uuGroupGetManagers', [groupName], ['list'])[0]);

            for manager in currentManagers - newManagers:
                self.icommand('imeta',  ['rm',  '-C', groupDir, 'administrator', manager])
            for manager in newManagers - currentManagers:
                self.icommand('imeta',  ['add', '-C', groupDir, 'administrator', manager])

        elif propertyName in ('category', 'subcategory'):
            self.icommand('imeta', [
                'set', '-C', groupDir, propertyName, value if len(value) else 'uncategorized'
            ])
        else:
            self.icommand('imeta', [
                'set', '-C', groupDir, propertyName, value if len(value) else '.'
            ])

    # }}}

    def __enter__(self):
        """
        'with' enter function.
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        'with' cleanup function.
        This would be a good place to put logout code if we wanted to do that.
        There's currently nothing to clean up.
        """
        pass

    def __init__(self, host, port, zone, clientUsername, adminUsername, adminPassword):
        """
        GroupManager constructor.

        Logs in with the given admin credentials.

        param host: iRODS connection details
        param port: iRODS connection details
        param zone: iRODS connection details
        param clientUsername: Username of the user initiating the manager action
        param adminUsername:  A rodsadmin's username
        param adminPassword:  A rodsadmin's password
        """
        try:
            self.clientUsername = clientUsername
            self.zone           = zone
        except Exception, ex:
            raise GmException(ex, 'Unknown user')

        self.env = os.environ.copy()
        self.env.update({
            'irodsHost':     str(host),
            'irodsPort':     str(port),
            'irodsZone':     str(zone),
            'irodsUserName': str(adminUsername),
        })

        # iinit does not check whether its stdin is a tty before trying to disable echo.
        # Use the -e switch to prevent ioctl errors.
        (out, err, status) = self.icommand('iinit', ['-e'], adminPassword, critical=False)

        if status != 0:
            raise GmException(
                  'iinit returned ' + str(status) + ', output follows:'
                + '\nICOMMAND STDOUT:\n' + out
                + '\nICOMMAND STDERR:\n' + err,
                'Unauthorized'
            )

if __name__ == '__main__':
    """
    Program entrypoint.
    """
    def fail(ex):
        """
        Safe general exception handler.

        Makes sure the program always exits with status 0 in order to allow
        the execCmd calling rule to read any error messages.

        iRODS only returns a valid execCmdOut object when our return
        value is zero. Trying to obtain stdout/stderr from an invalid
        execCmdOut crashes the agent.

        param ex: A GmException
        """
        print(ex.args[1], file=sys.stdout)
        print('Error:', ex.args[0], file=sys.stderr)

        exit(0) # Avoid segfaulting rodsAgent.

    try:
        with open(os.path.dirname(os.path.realpath(__file__))
                 + '/yoda-services.conf.json') as f:
            config = json.load(f)

            try:
                clientZone     = os.environ['spClientRodsZone']
                clientUsername = os.environ['spClientUser']
            except KeyError:
                raise GmException(
                    'spClient{User,RodsZone} environment variables missing',
                    'An internal error occurred. Please contact a Yoda administrator if problems persist.'
                )

            # Require the manager action initiating user to be in the same iRODS
            # zone as the server.
            if clientZone != config['zone']:
                raise GmException('User zone does not match iRODS server zone', 'Unauthorized')

            with GroupManager(
                host           = config['host'],
                port           = config['port'],
                zone           = config['zone'],
                clientUsername = clientUsername,
                adminUsername  = config['admin']['username'],
                adminPassword  = config['admin']['password'],
            ) as mgr:
                if len(sys.argv) >= 2:
                    if   sys.argv[1] == 'add'         and len(sys.argv) == 3:
                        mgr.groupAdd(sys.argv[2])
                    elif sys.argv[1] == 'set'         and len(sys.argv) == 5:
                        mgr.groupModify(sys.argv[2], sys.argv[3], sys.argv[4])
                    elif sys.argv[1] == 'add-user'    and len(sys.argv) == 4:
                        mgr.groupUserAdd(sys.argv[2], sys.argv[3])
                    elif sys.argv[1] == 'remove-user' and len(sys.argv) == 4:
                        mgr.groupUserRemove(sys.argv[2], sys.argv[3])
                    elif sys.argv[1] == 'remove-group' and len(sys.argv) == 3:
                        mgr.groupRemove(sys.argv[2])
                    else:
                        raise GmException('Invalid group-manager command', 'An internal error occurred. Please contact a Yoda administrator if problems persist.')
                else:
                    raise GmException('Incorrect parameter count', 'An internal error occurred. Please contact a Yoda administrator if problems persist.')
    except GmException, ex:
        fail(ex)
    except:
        fail(GmException(sys.exc_info()[1], 'An internal error occurred, please contact a Yoda administrator.'))
