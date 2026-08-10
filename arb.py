"""Functions for automatic resource balancing module."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['rule_resource_update_resc_arb_data',
           'rule_resource_update_misc_arb_data']


@rule.make(inputs=[0, 1, 2], outputs=[])
def rule_resource_update_resc_arb_data(ctx: rule.Context, resc_name: str, bytes_free: int, bytes_total: int) -> None:
    """
    Update ARB data for a specific resource

    :param ctx:         Combined type of a callback and rei struct
    :param resc_name:   Name of a particular unixfilesystem resource
    :param bytes_free:  Free size on this resource, in bytes
    :param bytes_total: Total size of this resource, in bytes
    """
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "Error: insufficient permissions to run ARB data update rule.")
        return

    if not resources.exists(ctx, resc_name):
        log.write(ctx, f"Error: could not find resource named '{resc_name}' for ARB update.")
        return

    bytes_free_gb = int(bytes_free) / 2 ** 30
    bytes_free_percent = 100 * (float(bytes_free) / float(bytes_total))

    if resc_name in config.arb_exempt_resources:
        arb_status = constants.arb_status.EXEMPT
    elif bytes_free_gb >= config.arb_min_gb_free and bytes_free_percent > config.arb_min_percent_free:
        arb_status = constants.arb_status.AVAILABLE
    else:
        arb_status = constants.arb_status.FULL

    parent_resc_name = resources.get_parent_by_name(ctx, resc_name)

    manager = arb_data_manager.ARBDataManager()
    manager.put(ctx, resc_name, constants.arb_status.IGNORE)

    if parent_resc_name is not None and resources.get_type_by_name(ctx, parent_resc_name) == "passthru":
        manager.put(ctx, parent_resc_name, arb_status)


@rule.make()
def rule_resource_update_misc_arb_data(ctx: rule.Context) -> None:
    """Update ARB data for resources that are not covered by the regular process. That is,
       all resources that are neither unixfilesystem nor passthrough resources, as well as
       passthrough resources that do not have a unixfilesystem child resource.

       :param ctx: Combined type of a callback and rei struct
    """
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "Error: insufficient permissions to run ARB data update rule.")
        return

    manager = arb_data_manager.ARBDataManager()

    all_resources = resources.get_all_resource_names(ctx)
    ufs_resources = set(resources.get_resource_names_by_type(ctx, "unixfilesystem")
                        + resources.get_resource_names_by_type(ctx, "unix file system"))
    pt_resources  = set(resources.get_resource_names_by_type(ctx, "passthru"))

    for resc in all_resources:
        if resc in ufs_resources:
            pass
        elif resc not in pt_resources:
            manager.put(ctx, resc, constants.arb_status.IGNORE)
        else:
            child_resources = resources.get_children_by_name(ctx, resc)
            child_found = False
            for child_resource in child_resources:
                if child_resource in ufs_resources:
                    child_found = True
            # Ignore the passthrough resource if it does not have a UFS child resource
            if not child_found:
                manager.put(ctx, resc, constants.arb_status.IGNORE)
