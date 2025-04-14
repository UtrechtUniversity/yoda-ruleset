"""Utility functions for measuring code coverage on development systems."""

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os

import coverage


def start_coverage():
    ruleset_path = "/etc/irods/yoda-ruleset"
    data_file = "/tmp/coverage.dat"
    source_paths = [ruleset_path, os.path.join(ruleset_path, "util")]
    cov = coverage.Coverage(source=source_paths, data_file=data_file)
    cov.set_option("run:parallel", True)
    cov.start()
    return cov


def stop_coverage(cov):
    cov.stop()
    cov.save()
