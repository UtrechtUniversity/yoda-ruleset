# -*- coding: utf-8 -*-
"""Yoda core ruleset containing iRODS and Python rules and policies useful for all Yoda environments."""

__version__   = '1.8.0'
__copyright__ = 'Copyright (c) 2015-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__author__    =  ('Felix Croes'
              + ', Paul Frederiks'
              + ', Jan de Mooij'
              + ', Harm de Raaff'
              + ', Chris Smeele'
              + ', Ton Smeele'
              + ', Lazlo Westerhof')
# (in alphabetical order)

# Import all modules containing rules into the package namespace,
# so that they become visible to iRODS.

import sys
sys.path.extend([ '/etc/irods/rules_uu', '/etc/irods/rules_uu/util', '/etc/irods/rules_uu/avu_json' ])

from browse                 import *
from folder                 import *
from groups                 import *
from json_datacite41        import *
from json_landing_page      import *
from mail                   import *
from meta                   import *
from meta_form              import *
from provenance             import *
from research               import *
from resources              import *
from schema                 import *
from schema_transformation  import *
from schema_transformations import *
from vault                  import *
from datacite               import *
from epic                   import *
from publication            import *
from policies               import *
from replication            import *
from revisions              import *
from settings               import *
from notifications          import *

# Import certain modules only when enabled.
from .util.config import config

if config.enable_intake:
    from intake import *
    from intake_vault import *

if config.enable_datarequest:
    from datarequest import *

if config.enable_deposit:
    from deposit import *

if config.enable_tokens:
    from data_access_token import *

if config.enable_tape_archive:
    from tape_archive import *
