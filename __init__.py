# -*- coding: utf-8 -*-
"""iRODS ruleset containing rules and policies useful for all Yoda environments."""

__copyright__ = 'Copyright (c) 2015-2019, Utrecht University'
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

from browse                 import *
from folder                 import *
from group                  import *
from integrity              import *
from json_datacite41        import *
from json_landing_page      import *
from meta                   import *
from meta_form              import *
from provenance             import *
from published_xml_to_json  import *
from research               import *
from resources              import *
from schema                 import *
from schema_transformation  import *
from schema_transformations import *
from vault                  import *
from vault_xml_to_json      import *
from datacite               import *
from epic                   import *
