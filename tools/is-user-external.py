#!/usr/bin/env python3
"""This script is used by the PAM stack to verify whether
   a user is external, based on the username."""

__copyright__ = 'Copyright (c) 2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../util"))

from yoda_names import is_internal_user

username = os.environ.get("PAM_USER", "")
exit_code = 1 if is_internal_user(username) else 0
sys.exit(exit_code)
