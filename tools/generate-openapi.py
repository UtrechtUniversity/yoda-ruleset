#!/usr/bin/env python2

"""Yoda API OpenAPI documentation generator.

This extracts all Yoda API functions from a ruleset, and generates an OpenAPI
file based on the function signatures and docstrings.

Note: depending on ruleset installation directory, you may need to run this
with a custom PYTHONPATH environment variable. By default /etc/irods is
included in the search path for ruleset imports.

This module imports (and therefore executes) ruleset code.
Do not run it on untrusted codebases.
"""
from __future__ import print_function

__copyright__ = 'Copyright (c) 2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__author__    =  ('Chris Smeele')
# (in alphabetical order)

import sys
import re
import inspect
import json

from importlib import import_module
from collections import OrderedDict

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('ruleset', metavar='RULESET', type=str,
                    help='a Python module/package name for an iRODS ruleset')

args = parser.parse_args()
ruleset_name = args.ruleset


# Strategy: Import the requested ruleset with an instrumented environment, and
# apply introspection to extract API function information.

# First we work on our environment:

class Sandbag(object):
    """A sturdy object that does not mind being pushed around.

    Used as a stub for various internal irods modules so that we can import
    rulesets without errors.
    """
    def __init__(self, *_, **kw): self._data = kw
    def __call__(self, *_, **__): return Sandbag()
    def __getattr__(self, k):     return self._data.get(k, Sandbag())
    def __setattr__(self, k, v):
        if k == '_data':
            return super(Sandbag, self).__setattr__(k, v)


class api(object):
    """Injected util.api module that intercepts all API function declarations.

    Alternatively we could dir() the ruleset module and extract functions that
    way, but that results in a mess.
    By replacing the API decorator instead we can preserve order of
    declarations, allowing for a more logical documentation structure.
    """
    fns = []

    @staticmethod
    def make():
        def f(g):
            api.fns += [(g.__name__, g)]
            return g
        return f

# Inject iRODS modules.
sys.modules['irods_types']       = Sandbag()
sys.modules['genquery']          = Sandbag()
sys.modules['session_vars']      = Sandbag()

# Inject the API shim, and its parent modules if needed.
if ruleset_name != 'rules_uu':
    sys.modules['rules_uu']      = Sandbag(util = Sandbag(api = api))
    sys.modules['rules_uu.util'] = Sandbag(api = api)
sys.modules['rules_uu.util.api'] = api

# Rulesets should be usable anywhere in PYTHONPATH.
# Add the iRODS directory to it for convenience.
sys.path += ['/etc/irods']

try:
    # Import the ruleset.
    ruleset_mod = import_module(ruleset_name)
except Exception as e:
    print('Could not import ruleset <{}>: {}'.format(ruleset_name, e), file=sys.stderr)
    raise


# Create an OpenAPI document.

# ... base template

# Note: for the most part, order matters (e.g. ordering of API function list).
#       So we use ordered dicts.
O = lambda *xs: OrderedDict(xs)

spec = O(('openapi', '3.0.0'),
         ('info',
         O(('description', ruleset_mod.__doc__),
           ('contact',
           O(('email', 'yoda@example.com'))),
           ('version', getattr(ruleset_mod, '__version__', '9999')),
           ('title', 'iRODS ruleset ' + ruleset_name))),
         ('servers',
          [O(('url', 'https://portal.yoda.test/api'), ('description', 'Local Yoda test server')),
           O(('url', 'https://yoda.test/api'),        ('description', 'Local Yoda2 test server'))]),
         ('security', [ O(('cookieAuth', [])), O(('basicAuth', [])) ]),
         ('components',
         O(('schemas',
          O(('result_error',
            O(('type', 'object'),
              ('properties',
              O(('status',      O(('type', 'string'), ('description', 'Holds an error ID'))),
                ('status_info', O(('type', 'string'), ('description', 'Holds a human-readable error description'))),
                ('data',
                O(('description', 'empty'),
                  ('nullable', True),
                  ('type', 'object'))))))))),
            ('securitySchemes',
            O(('cookieAuth',
              O(('in', 'cookie'),
                ('type', 'apiKey'),
                # ('name', 'session'))),
                ('name', 'yoda_session'))),
              ('basicAuth', O(('type', 'http'), ('scheme', 'basic'))))),
            ('responses',
            O(('status_500',
              O(('description', 'Error'),
                ('content',
                O(('application/json',
                  O(('schema', O(('$ref', '#/components/schemas/result_error'))))))))))))),
         ('paths', O())
      )

def gen_fn_spec(name, fn):
    """Generate OpenAPI spec for one function (one path)"""

    name = re.sub('^api_', '', name)
    mod  = fn.__module__.replace(ruleset_name+'.', '')

    print('{}/{}'.format(mod, name), file=sys.stderr)

    # Convert function signature -> argument spec.
    # TODO: Python3: Extract type annotations.
    #                Also see https://docs.python.org/3.8/library/typing.html#typing.TypedDict
    #                for annotation of complex structures.

    a_pos, a_var, a_kw, a_defaults = inspect.getargspec(fn)

    a_pos = a_pos[1:]  # ignore callback/context param.

    required = a_pos if a_defaults is None else a_pos[:-len(a_defaults) ]
    optional = []    if a_defaults is None else a_pos[ -len(a_defaults):]

    doc = fn.__doc__ or '(undocumented)'

    # Map Python types to JSON schema types.
    types = {'str':  'string'
            ,'int':  'integer'
            ,'bool': 'boolean'
            ,'dict': 'object'
            ,'list': 'array'}

    paramdocs = O(*[(k, (types[(re.findall(r'^\s*:type\s+' +re.escape(k)+r':\s*(.+?)\s*$', doc, re.M) or ['str'])[-1]],
                         (re.findall(r'^\s*:param\s+'+re.escape(k)+r':\s*(.+?)\s*$', doc, re.M) or ['(undocumented)'])[-1],
                         None if i < len(required) else a_defaults[i-len(required)]))
                      for i, k in enumerate(required+optional)])

    # Sphinx-compatible parameter documentation.
    doc = re.sub(r'^\s*:param.*?\n', '', doc, flags=re.M|re.S)
    doc = re.sub(r'^\s*:type.*?\n',  '', doc, flags=re.M|re.S)

    req = list(required)
    props = O(*[(name, { 'type':        paramdocs[name][0],
                         'description': paramdocs[name][1],
                         'default':     paramdocs[name][2] })
                for name in required+optional])

    for name in required+optional:
        if props[name]['type'] == 'array':
            props[name]['items'] = O()

    dataspec = {
        'type': 'object',
        'required': req,
        'properties': props
    }

    # Silly.
    if req == []: del dataspec['required']

    # Currently, arguments are specified as a JSON string in a a
    # multipart/form-data argument. This leads to less-than-ideal presentation
    # of (optional) arguments in the Swagger editor.
    # It seems to be a good idea to move the toplevel attributes of argument
    # data to actual request parameters (e.g. individual form "fields").

    return O(
      ('post',
      O(('tags', [mod]),
        ('summary', doc),
        ('requestBody',
        O(('required', True),
          ('content',
          # How do we encode arguments?
          #
          # 1) as a JSON 'data' property
          # This is in line with the current PHP Yoda portal,
          # but as a result parameter documentation is unaccessible from swagger,
          # and optional parameters are missing completely.
          #
          # O(('multipart/form-data',
          #   O(('schema',
          #     O(('type', 'object'),
          #       ('properties',
          #       O(('data', dataspec))))))))))),
          #
          # 2) as a JSON request body. Same result as (1)
          #
          # O(('application/json',
          #   O(('schema', dataspec))))))),
          #
          # 3) Toplevel parameters as form fields.
          # Not in line with the current portal,
          # but provides the best documentation value.
          #
          O(('multipart/form-data',
            O(('schema', dataspec))))))),
        ('responses',
        O(('200',
          O(('description', 'Success'),
            ('content',
            O(('application/json',
              O(('schema',
                O(('type', 'object'),
                  ('properties',
                  O(('status',      O(('type', 'string'))),
                    ('status_info', O(('type', 'string'), ('nullable', True))),
                    ('data',        O(('nullable', True))))))))))))),
          ('500', O(('$ref', '#/components/responses/status_500'))))))))

for name, fn in api.fns:
    if '<lambda>' in name:
        # Ignore weird undocumented inline definitions.
        continue

    spec['paths'].update([('/'+name, gen_fn_spec(name, fn))])

print(json.dumps(spec))
