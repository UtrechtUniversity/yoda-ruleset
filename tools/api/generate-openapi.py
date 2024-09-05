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

__copyright__ = 'Copyright (c) 2020-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

__author__    =  ('Chris Smeele')
__author__    =  ('Lazlo Westerhof')
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
parser.add_argument('--core', dest='core', action='store_const', const=True, default=False,
                    help='only generate core API')
parser.add_argument('--module', action="store", dest="module", default=False,
                    help='only generate API of specific module')

args = parser.parse_args()
ruleset_name = args.ruleset
core = args.core
module = args.module

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

# Inject other modules.
sys.modules['pysqlcipher3']      = Sandbag()

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
def oDict(*xs):
    return OrderedDict(xs)

title = 'Yoda API'
if core:
    title = 'Yoda core API'
if module:
    title = 'Yoda {} API'.format(module)

spec = oDict(('openapi', '3.0.0'),
         ('info',
         oDict(('description', ruleset_mod.__doc__),
           ('contact',
           oDict(('email', 'l.r.westerhof@uu.nl'))),
           ('version', getattr(ruleset_mod, '__version__', '9999')),
           ('title', title))),
         ('servers',
          [oDict(('url', 'https://portal.yoda.test/api'), ('description', 'Local Yoda development server'))]),
         ('security', [ oDict(('cookieAuth', [])), oDict(('basicAuth', [])) ]),
         ('components',
         oDict(('schemas',
          oDict(('result_error',
            oDict(('type', 'object'),
              ('properties',
              oDict(('status',      oDict(('type', 'string'), ('description', 'Holds an error ID'))),
                ('status_info', oDict(('type', 'string'), ('description', 'Holds a human-readable error description'))),
                ('data',
                oDict(('description', 'empty'),
                  ('nullable', True),
                  ('type', 'object'))))))))),
            ('securitySchemes',
            oDict(('cookieAuth',
              oDict(('in', 'cookie'),
                ('type', 'apiKey'),
                # ('name', 'session'))),
                ('name', 'yoda_session'))),
              ('basicAuth', oDict(('type', 'http'), ('scheme', 'basic'))))),
            ('responses',
            oDict(('status_400',
              oDict(('description', 'Bad request'),
                ('content',
                oDict(('application/json',
                  oDict(('schema', oDict(('$ref', '#/components/schemas/result_error'))))))))),
              ('status_500',
                oDict(('description', 'Internal error'),
                  ('content',
                  oDict(('application/json',
                    oDict(('schema', oDict(('$ref', '#/components/schemas/result_error'))))))))),
             )))),
         ('paths', oDict())
      )

def gen_fn_spec(name, fn):
    """Generate OpenAPI spec for one function (one path)"""
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

    paramdocs = oDict(*[(k, (types[(re.findall(r'^\s*:type\s+' +re.escape(k)+r':\s*(.+?)\s*$', doc, re.MULTILINE) or ['str'])[-1]],
                         (re.findall(r'^\s*:param\s+'+re.escape(k)+r':\s*(.+?)\s*$', doc, re.MULTILINE) or ['(undocumented)'])[-1],
                         None if i < len(required) else a_defaults[i-len(required)]))
                      for i, k in enumerate(required+optional)])

    # Sphinx-compatible parameter documentation.
    doc = re.sub(r'^\s*:param.*?\n', '', doc, flags=re.MULTILINE|re.DOTALL)
    doc = re.sub(r'^\s*:type.*?\n',  '', doc, flags=re.MULTILINE|re.DOTALL)

    # Only retrieve summary.
    doc = re.sub(r'^\s*[\r\n].*', '', doc, flags=re.MULTILINE|re.DOTALL)

    req = list(required)
    props = oDict(*[(name, { 'type':        paramdocs[name][0],
                         'description': paramdocs[name][1],
                         'default':     paramdocs[name][2] })
                for name in required+optional])

    for name in required+optional:
        if props[name]['type'] == 'array':
            props[name]['items'] = oDict()

    dataspec = {
        'type': 'object',
        'required': req,
        'properties': props
    }

    # Silly.
    if req == []:
        del dataspec['required']

    # Currently, arguments are specified as a JSON string in a a
    # multipart/form-data argument. This leads to less-than-ideal presentation
    # of (optional) arguments in the Swagger editor.
    # It seems to be a good idea to move the toplevel attributes of argument
    # data to actual request parameters (e.g. individual form "fields").

    return oDict(
      ('post',
      oDict(('tags', [mod]),
        ('summary', doc),
        ('requestBody',
        oDict(('required', True),
          ('content',
          # How do we encode arguments?
          #
          # 1) as a JSON 'data' property
          # This is in line with the current PHP Yoda portal,
          # but as a result parameter documentation is unaccessible from swagger,
          # and optional parameters are missing completely.
          #
          # oDict(('multipart/form-data',
          #   oDict(('schema',
          #     oDict(('type', 'object'),
          #       ('properties',
          #       oDict(('data', dataspec))))))))))),
          #
          # 2) as a JSON request body. Same result as (1)
          #
          # oDict(('application/json',
          #   oDict(('schema', dataspec))))))),
          #
          # 3) Toplevel parameters as form fields.
          # Not in line with the current portal,
          # but provides the best documentation value.
          #
          oDict(('application/json',
            oDict(('schema', dataspec))))))),
        ('responses',
        oDict(('200',
          oDict(('description', 'Success'),
            ('content',
            oDict(('application/json',
              oDict(('schema',
                oDict(('type', 'object'),
                  ('properties',
                  oDict(('status',      oDict(('type', 'string'))),
                    ('status_info', oDict(('type', 'string'), ('nullable', True))),
                    ('data',        oDict(('nullable', True))))))))))))),
          ('400', oDict(('$ref', '#/components/responses/status_400'))),
          ('500', oDict(('$ref', '#/components/responses/status_500'))))))))

for name, fn in api.fns:
    if '<lambda>' in name:
        # Ignore weird undocumented inline definitions.
        continue

    name = re.sub('^api_', '', name)

    if core:
        modules = ['datarequest', 'deposit', 'intake']
        if name.startswith(tuple(modules)):
            continue

    if module:
        if not name.startswith(module):
            continue

    spec['paths'].update([('/'+name, gen_fn_spec(name, fn))])

print(json.dumps(spec))
