#!/usr/bin/env python

""" This script updates all local unixfilesystem resources with the following parameters:
    - Minimum permissible amount of free space for creating data objects (based on percentage of total
      volume size and/or an absolute limit)
    - Current amount of free space on the volume

    The unixfilesystem resource plugin will use these parameters to determine whether new data objects
    can still be created on the resource.
"""

import argparse
import json
import os
import psutil
import socket
import ssl
import sys

from irods.column import In
from irods.models import Resource
from irods.password_obfuscation import decode as password_decode
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
    parser.add_argument("-e", "--exempt-resources",
                        help="Resources that should not be updated by the script (comma-separated list).",
                        type=str, required=False, default="")
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Show verbose information about what the script is doing.")
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser(
        "clear", help="Clear minimum permissible free space parameters.")

    parser_update = subparsers.add_parser(
        "update", help="Update current and minimum free space on resources.")
    parser_update.add_argument("--min-percent-free", type=int, default=5,
                               help="Minimum relative free space in percent (default: 5)")
    parser_update.add_argument("--min-gb-free", type=int, default=0,
                               help="Minimum absolute free space in GB (default: 0)")

    result = parser.parse_args()

    if result.subcommand == "update":
        if result.min_percent_free < 0 or result.min_percent_free > 100:
            sys.exit(
                "Error: minimum free percentage should be between 0 and 100 (inclusive)")
        if result.min_gb_free < 0:
            sys.exit("Error: minimum free value should be positive.")

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


def get_all_ufs_resources(session):
    results = session.query(Resource.name).filter(
        In(Resource.type, ["unixfilesystem", "unix file system"])).filter(
        Resource.location == get_hostname()).all()
    return sorted(list(map(lambda g: g[Resource.name], results)))


def get_volume_min(vault_path, min_percent_free, min_gb_free):
    relative_minimum = (float(min_percent_free) / 100) * \
        get_volume_total(vault_path)
    absolute_minimum = int(min_gb_free) * 1024 ** 3
    return int(max(relative_minimum, absolute_minimum))


def process_resources(session, resource_names, subcommand,
                      verbose_mode, min_percent_free, min_gb_free):
    for resource_name in resource_names:
        if verbose_mode:
            print("Processing resource {} ...".format(resource_name))
        resource = session.resources.get(resource_name)

        if subcommand == "clear":
            # iRODS does not accept an empty string here, so we will clear it
            # to a single space
            new_context = " "
            new_freespace = None
        elif subcommand == "update":
            new_context = "minimum_free_space_for_create_in_bytes={}".format(
                get_volume_min(resource.vault_path, min_percent_free, min_gb_free))
            new_freespace = get_volume_free(resource.vault_path)
        else:
            raise Exception("Unknown subcommand: " + subcommand)

        if resource.context != new_context:
            if verbose_mode:
                print("Updating context of resource {} from '{}' to '{}' ...".format(
                    resource_name, resource.context, new_context))
            session.resources.modify(resource_name, "context", new_context)

        if new_freespace is not None and str(
                resource.free_space) != str(new_freespace):
            if verbose_mode:
                print("Updating free space of resource {} from {} to {} ...".format(
                    resource_name, resource.free_space, new_freespace))
            session.resources.modify(
                resource_name, "free_space", new_freespace)


def main():
    args = parse_args()
    env = get_irods_environment()
    session = setup_session(env)
    all_resources = get_all_ufs_resources(session)
    exempt_resources = args.exempt_resources.split(",")
    resources_to_update = [
        resource for resource in all_resources if resource not in exempt_resources]
    process_resources(session,
                      resources_to_update,
                      args.subcommand,
                      args.verbose,
                      args.min_percent_free if args.subcommand == "update" else None,
                      args.min_gb_free if args.subcommand == "update" else None)


if __name__ == '__main__':
    main()
