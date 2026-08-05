#!/usr/bin/env python3

"""Yoda API OpenAPI documentation generator.

This extracts all Yoda API functions from the ruleset, and generates an OpenAPI
file based on the function signatures and docstrings.
"""

__copyright__ = 'Copyright (c) 2020-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import argparse
import ast
import json
import os
import re
import sys
from collections import OrderedDict
from glob import glob
from typing import Any, Dict, Tuple, Union


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--core', dest='core', action='store_const', const=True, default=False,
                       help='only generate core API')
    group.add_argument('--module', action="store", dest="module", default=None,
                       help='only generate API of specific module')
    return parser.parse_args()


def get_ruleset_dir() -> str:
    return os.path.join(os.path.realpath(os.path.dirname(__file__)), "../..")


def get_ast_tree_of_file(ruleset_dir: str, ruleset_file: str):
    init_file = os.path.join(ruleset_dir, ruleset_file)
    with open(init_file, 'r') as file:
        tree = ast.parse(file.read(), filename=init_file)
    return tree


def oDict(*xs: Tuple) -> OrderedDict:
    return OrderedDict(xs)


def get_openapi_template(ruleset_description: Union[str, None], ruleset_version: Union[str, None],
                         core: bool, module: str) -> OrderedDict:
    """Create an OpenAPI document base template

       Note: for the most part, order matters (e.g. ordering of API function list).
       So we use ordered dicts.
    """

    title = 'Yoda API'
    if core:
        title = 'Yoda core API'
    if module:
        title = 'Yoda {} API'.format(module)

    ruleset_description_str = ruleset_description if ruleset_description is not None else "N/A"
    ruleset_version_str = ruleset_version if ruleset_version is not None else '9999'

    spec = oDict(('openapi', '3.0.0'),
                 ('info',
                  oDict(('description', ruleset_description_str),
                        ('contact',
                         oDict(('email', 'l.r.westerhof@uu.nl'))),
                        ('version', ruleset_version_str),
                        ('title', title))),
                 ('servers',
                  [oDict(('url', 'https://portal.yoda.test/api'), ('description', 'Local Yoda development server'))]),
                 ('security', [oDict(('cookieAuth', [])),
                  oDict(('basicAuth', []))]),
                 ('components',
                  oDict(('schemas',
                         oDict(('result_error',
                                oDict(('type', 'object'),
                                      ('properties',
                                       oDict(('status', oDict(('type', 'string'), ('description', 'Holds an error ID'))),
                                             ('status_info', oDict(('type', 'string'), ('description',
                                                                                        'Holds a human-readable error description'))),
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
    return spec


def _extract_optional_inner(input: str) -> str:
    """Convert Optional[T] / typing.Optional[T] into T."""
    s = input.strip()

    # Optional[str] / typing.Optional[str].
    m = re.match(r'^(?:typing\.)?Optional\[(.+)\]$', s)
    if m:
        return m.group(1).strip()

    return input


def is_optional_annotation(input: str | None) -> bool:
    if not input:
        return False

    s = input.strip()

    # Optional[T] / typing.Optional[T]
    if re.match(r'^(?:typing\.)?Optional\[(.+)\]$', s):
        return True

    # T | None or None | T (PEP604 union)
    if re.search(r'^(\w+)\s*\|\s*[Nn]one$', s):
        return True
    if re.search(r'^[Nn]one\s*\|\s*(\w+)$', s):
        return True

    return False


def get_json_type(input: str) -> str:
    """Translate Python type to JSON type if a translation is available, otherwise use the Python type."""
    # Handle Optional[T] / typing.Optional[T] first.
    inner = _extract_optional_inner(input)

    # Handle the union form: T | None.
    match_nullable_type = re.search(r'^(\w+)\s*\|\s*[Nn]one$', inner)
    if match_nullable_type:
        inner = match_nullable_type[1]

    types_lookup_table = {
        'str': 'string',
        'int': 'integer',
        'bool': 'boolean',
        'dict': 'object',
        'Dict': 'object',
        'list': 'array',
        'List': 'array',
    }
    return types_lookup_table.get(inner, inner)


def is_nullable_type(input: str) -> bool:
    s = input.strip()

    # Optional[str] / typing.Optional[str]
    if re.match(r'^(?:typing\.)?Optional\[(.+)\]$', s):
        return True

    # T | None
    return bool(
        re.search(r'^(\w+)\s*\|\s*[Nn]one$', s)
        or re.search(r'^[Nn]one\s*\|\s*(\w+)$', s)
    )


def gen_fn_spec(function_name: str, function_properties: Dict):
    """Generate OpenAPI spec for one function (one path)"""
    doc: str = str(function_properties.get("doc")) if function_properties.get("doc") is not None else ""
    props = oDict()
    for arg_name in function_properties["args"]:
        arg_properties = function_properties["args"][arg_name]

        # Try to get type from docstring, otherwise from type annotation. If neither is available, assume it's as string
        doc_py_type = re.findall(r'^\s*:type\s+' + re.escape(function_name) + r':\s*(.+?)\s*$', doc, re.MULTILINE)
        ann_py_type = arg_properties["annotation"]
        py_type = doc_py_type[-1] if len(doc_py_type) > 0 else (ann_py_type if ann_py_type is not None else "str")
        json_type = get_json_type(py_type)
        nullable_type = is_nullable_type(py_type)

        search_param_pattern: str = r'^\s*:param\s+' + re.escape(arg_name) + r':\s*(.+?)\s*$'
        arg_description = (re.findall(search_param_pattern, str(doc), re.MULTILINE) or ['(undocumented)'])[-1]

        arg_default = arg_properties["default_value"]

        props[arg_name] = {"type": json_type,
                           "description": arg_description,
                           "default": arg_default,
                           "nullable": nullable_type}

    # Remove everything but the summary from the docstring
    doc = re.sub(r'^\s*:param.*?\n', '', doc, flags=re.MULTILINE | re.DOTALL)
    doc = re.sub(r'^\s*:type.*?\n', '', doc, flags=re.MULTILINE | re.DOTALL)
    doc = re.sub(r'^\s*[\r\n].*', '', doc, flags=re.MULTILINE | re.DOTALL)

    for name in props:
        if props[name]['type'] == 'array':
            props[name]['items'] = oDict()

    dataspec = {
        'type': 'object',
        'required': [arg_name for arg_name in function_properties["args"]
                     if function_properties["args"][arg_name]["required"]],
        'properties': props
    }

    tags = [function_properties["tag"]]

    # Silly.
    if dataspec['required'] == []:
        del dataspec['required']

    # Currently, arguments are specified as a JSON string in a a
    # multipart/form-data argument. This leads to less-than-ideal presentation
    # of (optional) arguments in the Swagger editor.
    # It seems to be a good idea to move the toplevel attributes of argument
    # data to actual request parameters (e.g. individual form "fields").

    return oDict(
        ('post',
         oDict(('tags', tags),
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
                                                   oDict(('status', oDict(('type', 'string'))),
                                                         ('status_info', oDict(
                                                          ('type', 'string'), ('nullable', True))),
                                                         ('data', oDict(('nullable', True))))))))))))),
                      ('400', oDict(('$ref', '#/components/responses/status_400'))),
                      ('500', oDict(('$ref', '#/components/responses/status_500'))))))))


def add_api_data_to_spec(
        spec: OrderedDict, api_function_data: OrderedDict, core: bool, module: str) -> None:
    """Add collected information about API functions to the output document."""
    for function_name in api_function_data:
        if '<lambda>' in function_name:
            # Ignore weird undocumented inline definitions.
            continue

        name = re.sub('^api_', '', function_name)

        if core:
            modules = ['datarequest', 'deposit']
            if name.startswith(tuple(modules)):
                continue

        if module:
            if not name.startswith(module):
                continue

        spec['paths'].update(
            [('/' + name, gen_fn_spec(function_name, api_function_data[function_name]))])


def get_ruleset_description(ruleset_dir: str) -> Union[str, None]:
    """Get the global doc string of the ruleset"""
    tree = get_ast_tree_of_file(ruleset_dir, "__init__.py")
    return ast.get_docstring(tree)


def get_ruleset_version(ruleset_dir) -> Union[str, None]:
    """Get the global version of the ruleset"""
    tree = get_ast_tree_of_file(ruleset_dir, "__init__.py")
    version = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return version


def get_api_function_data(ruleset_dir: str, core: bool, module: str) -> OrderedDict:
    """Collect argument, docstring and decorator information for API functions."""
    result = oDict()
    ruleset_source_files = glob(os.path.join(ruleset_dir, "*.py"))
    for source_file in ruleset_source_files:
        with open(source_file, "r") as file:
            tree = ast.parse(file.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name

                if not function_name.startswith("api_"):
                    continue

                def _get_argument_data(node):
                    argdata = oDict()
                    for i, arg in enumerate(node.args.args):

                        if i == 0:
                            continue  # Skip the internal context argument

                        arg_name = arg.arg
                        annotation = None
                        if arg.annotation:
                            annotation = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None

                        default_value = None
                        required = True

                        # Determine required from whether a default is present in the signature.
                        if i >= len(node.args.args) - len(node.args.defaults):
                            default_index = i - (len(node.args.args) - len(node.args.defaults))
                            default_value = ast.unparse(node.args.defaults[default_index]) if hasattr(ast, 'unparse') else None
                            required = False

                        # Optional[...] / T | None implies not required.
                        if is_optional_annotation(annotation):
                            required = False

                        argdata[arg_name] = {
                            "annotation": annotation,
                            "default_value": default_value,
                            "required": required
                        }

                    return argdata

                function_properties: dict[str, Any] = {}
                function_properties["doc"] = ast.get_docstring(node)
                function_properties["args"] = _get_argument_data(node)
                function_properties["tag"] = os.path.basename(source_file)[:-3]
                function_properties["decorators"] = [
                    ast.unparse(decorator) if hasattr(ast, 'unparse') else None
                    for decorator in node.decorator_list
                ]
                if "api.make()" in function_properties["decorators"]:
                    result[function_name] = function_properties
    return result


def main(args: argparse.Namespace) -> None:
    ruleset_dir = get_ruleset_dir()
    ruleset_description = get_ruleset_description(ruleset_dir)
    ruleset_version = get_ruleset_version(ruleset_dir)
    api_function_data = get_api_function_data(ruleset_dir, args.core, args.module)
    spec = get_openapi_template(ruleset_description, ruleset_version, args.core, args.module)
    add_api_data_to_spec(spec, api_function_data, args.core, args.module)
    print(json.dumps(spec))


if __name__ == "__main__":
    args = get_args()
    main(args)
