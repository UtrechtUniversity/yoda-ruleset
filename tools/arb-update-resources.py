#!/usr/bin/env python3

""" This script collects and submits data needed for Automatic Resource Balancing (ARB): the
    process of ensuring that new data objects get created on resources that still have space available.

    It does the following things:
    - Gather free space and total space for all local unixfilesystem resources
    - Pass this data to the ARB update rule, so that it can be taken into account by ARB.
    - If the script is run on the provider, it also invokes the rule that initializes ARB data
      for resources that are not relevant to ARB. This makes ARB ignore these resources.
"""

import argparse
import json
import os
import psutil
import socket
import ssl

from io import StringIO
from collections import OrderedDict


from irods.column import In
from irods.models import Resource
from irods.password_obfuscation import decode as password_decode
from irods.rule import Rule
from irods.session import iRODSSession


def get_hostname():
    return socket.getfqdn()


def get_volume_total(path):
    return psutil.disk_usage(path).total


def get_volume_free(path):
    return psutil.disk_usage(path).free


def parse_args():
    '''Parse command line arguments'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Show verbose information about what the script is doing.")
    parser.add_argument("--override-free", type=str, default="",
                        help="Comma-separated list of free space overrides, e.g. 'resc1:1024,resc2:2048'")
    parser.add_argument("--override-total", type=str, default="",
                        help="Comma-separated list of total space overrides, e.g. 'resc1:1024,resc2:2048'")
    return parser.parse_args()


def parse_cs_values(input):
    """Parses a comma-separated list of key:value pairs as a dict."""
    result = dict()
    for kv_pair in input.split(","):
        if kv_pair == "":
            continue
        elif ":" not in kv_pair:
            raise Exception("Could not parse KV pair: " + kv_pair)
        else:
            result[kv_pair.split(":")[0]] = kv_pair.split(":")[1]
    return result


def get_irods_environment(
        irods_environment_file="/var/lib/irods/.irods/irods_environment.json"):
    """Reads the irods_environment.json file, which contains the environment
       configuration.

       :param str irods_environment_file filename of the iRODS environment file.;
       :return Data structure containing the configuration"""
    with open(irods_environment_file, 'r') as f:
        return json.load(f)


def setup_session(irods_environment_config,
                  ca_file="/etc/pki/tls/certs/chain.crt"):
    """Use irods environment files to configure a iRODSSession"""

    irodsA = os.path.expanduser("~/.irods/.irodsA")
    with open(irodsA, "r") as r:
        scrambled_password = r.read()
        password = password_decode(scrambled_password)

    ssl_context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        cafile=ca_file,
        capath=None,
        cadata=None)
    ssl_settings = {'client_server_negotiation': 'request_server_negotiation',
                    'client_server_policy': 'CS_NEG_REQUIRE',
                    'encryption_algorithm': 'AES-256-CBC',
                    'encryption_key_size': 32,
                    'encryption_num_hash_rounds': 16,
                    'encryption_salt_size': 8,
                    'ssl_context': ssl_context}
    settings = dict()
    settings.update(irods_environment_config)
    settings.update(ssl_settings)
    settings["password"] = password
    session = iRODSSession(**settings)
    return session


def get_local_ufs_resources(session):
    results = session.query(Resource.name).filter(
        In(Resource.type, ["unixfilesystem", "unix file system"])).filter(
        Resource.location == get_hostname()).all()
    return sorted(list(map(lambda g: g[Resource.name], results)))


def process_ufs_resources(session, resource_names, override_free_dict, override_total_dict, verbose_mode):
    for resource_name in resource_names:
        if verbose_mode:
            print("Processing resource {} ...".format(resource_name))

        resource = session.resources.get(resource_name)

        free_space = override_free_dict.get(resource_name, get_volume_free(resource.vault_path))
        total_space = override_total_dict.get(resource_name, get_volume_total(resource.vault_path))

        if verbose_mode:
            print("Setting free / total space of resource {} to {} / {}.".format(resource_name, free_space, total_space))
        call_rule_update_resc(session, resource_name, free_space, total_space)


def call_rule(session, rulename, params, number_outputs,
              rule_engine='irods_rule_engine_plugin-irods_rule_language-instance'):
    """Run a rule

       :param rulename: name of the rule
       :param params: dictionary of rule input parameters and their values
       :param number_output: number of output parameters
       :param rule_engine: rule engine to run rule on (defaults to legacy rule engine if none provided)
     """
    body = 'myRule {{\n {}('.format(rulename)

    for input_var in params.keys():
        body += "'*{}',".format(input_var)

    if len(params) > 0:
        # Remove trailing comma from input argument list
        body = body[:-1]

    body += '); writeLine("stdout","");}'

    input_params = {"*{}".format(k): '"{}"'.format(v) for (k, v) in params.items()}
    output_params = 'ruleExecOut'

    re_config = {'instance_name': rule_engine}

    myrule = Rule(
        session,
        rule_file=StringIO(body),
        params=input_params,
        output=output_params,
        **re_config)

    outArray = myrule.execute()
    buf = outArray.MsParam_PI[0].inOutStruct.stdoutBuf.buf.decode(
        'utf-8').splitlines()

    return buf[:number_outputs]


def call_rule_update_resc(session, resource, bytes_free, bytes_total):
    """ Calls rule to update data for a specific resource (and its parent resource)
    """
    parms = OrderedDict([
        ('resource', resource),
        ('bytes_free', bytes_free),
        ('bytes_total', bytes_total)])
    [out] = call_rule(session, 'rule_resource_update_resc_arb_data', parms, 1)


def call_rule_update_misc(session):
    """Calls rule to update resources to be ignored by ARB

    """
    parms = OrderedDict([])
    [out] = call_rule(session, 'rule_resource_update_misc_arb_data', parms, 1)


def is_on_provider():
    with open('/etc/irods/server_config.json', 'r') as f:
        config = json.load(f)
        return config["icat_host"] == get_hostname()


def main():
    args = parse_args()
    env = get_irods_environment()
    session = setup_session(env)
    override_free_dict = parse_cs_values(args.override_free)
    override_total_dict = parse_cs_values(args.override_total)
    local_ufs_resources = get_local_ufs_resources(session)
    process_ufs_resources(session,
                          local_ufs_resources,
                          override_free_dict,
                          override_total_dict,
                          args.verbose)

    if is_on_provider():
        if args.verbose:
            print("Updating misc resources ...")
        call_rule_update_misc(session)


if __name__ == '__main__':
    main()
