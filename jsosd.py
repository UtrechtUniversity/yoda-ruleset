#!/usr/bin/env python3

import json
import sys
import xml.etree.cElementTree as ET

from urllib.parse import urlparse, urljoin
from collections  import OrderedDict
from copy         import deepcopy
from functools    import reduce
from operator     import add
from argparse     import ArgumentParser

def flattenSchema(j, uri):
    """
    Given a dict representing a JSON schema object, resolve all contained $ref
    objects into references to actual Python objects.

    Only references within the same document are supported for now.
    """
    j = deepcopy(j) # Return a flattened schema, do not modify the input.
    documents = dict() # URL(?) => JSON document object
    #documents.add(uri)

    def resolvePath(doc, *path):
        if len(path) != 0:
            assert(path[0] in doc)
        return doc if len(path) == 0 else resolvePath(doc[path[0]], *path[1:])

    def flattenDocument(doc, uri):
        """Flatten the references for a single JSON document"""

        def flattenElement(el, fragment):
            """Flatten the references for a single JSON element"""

            def resolve(uri):
                """Resolve an URI (based on the current fragment)"""

                if not uri.startswith('#/'):
                    print('Only absolute references within the current document allowed for now')
                    assert(False)
                return resolvePath(doc, *uri[2:].split('/'))

            if isinstance(el, dict):
                if '$ref' in el:
                    # Resolve that reference.
                    el = resolve(el['$ref'])
                else:
                    # Nothing to see here, move on.
                    for k, v in el.items():
                        el[k] = flattenElement(v, fragment)
            elif isinstance(el, list):
                for i, v in enumerate(el):
                    el[i] = flattenElement(v, fragment)

            return el
        return flattenElement(doc, '/')
    return flattenDocument(j, uri)


def getTypes(obj):
    """
    Extract the type declarations from a JSON schema object.
    """
    return obj['definitions'] if 'definitions' in obj else {}

def El(tag, attrs=None, *children):
    """
    Construct an XML element with the given optional attributes and optional children.
    """
    el = ET.Element(tag, attrs if attrs is not None else {})
    for c in children:
        el.append(c)
    return el

def annotateTypes(j):
    """
    Annotate type declaration structures with the key (typename) pointing to them.
    This ensures that elements that reference a type through $ref also know the type's name.
    """
    j = deepcopy(j)
    for k, v in getTypes(j).items():
        assert(isinstance(v, dict))
        v.jsosd_typename = k
    return j

def markRequiredElements(elements, required):
    for child in filter(lambda x: x.get('name') in required, elements):
        child.set('minOccurs', '1')

def convertType(body, typename=None):
    """
    Generate a type or an element.
    """
    v = body # XXX

    if 'jsosd_typename' in dir(body) and typename is None:
        # Return an element of this type.
        return [El('xs:element',
                   {'name': fieldname, 'type': v.jsosd_typename})]

    assert('type' in v)

    typ = None # The generated type, either a string (name), or an element describing the type.

    if 'yoda:structure' in v and v['yoda:structure'] in ('compound', 'subproperties'):

        assert('properties' in v)

        # Convert child elements.
        subs = reduce(add, [convertProperty(k, v) for k, v in v['properties'].items()], [])
        #subs = reduce(add, [convertType(v, None, k) for k, v in v['properties'].items()], [])

        # Annotate requiredness.
        if 'required' in v:
            markRequiredElements(subs, v['required'])

        assert('comment' not in v or v['comment'] != 'group')
        # For compound / subproperties, add three levels.
        typ = El('xs:complexType',
                 {} if typename is None else {'name': typename},
                 El('xs:sequence', {},
                    *subs))

    elif 'enum' in v:
        # Type should be string, or the like.
        assert(v['type'] in builtinTypes())
        enumType = builtinTypes()[v['type']] if v['type'] in builtinTypes() else v['type']

        typ = El('xs:simpleType',
                 {} if typename is None else {'name': typename},
                 El('xs:restriction', {'base': enumType},
                    # Turn the possible enum values into xs:enumeration tags.
                    *map(lambda val: El('xs:enumeration', {'value': val}),
                         v['enum'])))

    elif v['type'] in builtinTypes():
        # Simple builtin type.
        typ = builtinTypes()[v['type']]

    else:
        # Unknown type.
        print('paniek: ' + str(typename), file=sys.stderr)
        sys.exit(1)

    if len(set(['maxLength']) & set(v.keys())):
        # Only allow extra restrictions if the base type can be specified by name.
        assert(isinstance(typ, str))

        restriction = El('xs:restriction',
                         {'base': typ})
        if 'maxLength' in v:
            restriction.append(El('xs:maxLength',
                                  {'value': str(v['maxLength'])}))
        typ = El('xs:simpleType',
                 {} if typename is None else {'name': typename},
                 restriction)

    if typename is None:
        return typ
    else:
        if isinstance(typ, str):
            # We are declaring a type, so we are forced to create a type element.
            return El('xs:simpleType',
                      {'name': typename},
                      El('xs:restriction',
                         {'base': typ}))
        else:
            return typ

def convertProperty(name, body):
    if 'jsosd_typename' in dir(body):
        # Return an element of this type.
        el = El('xs:element',
                {'name': name, 'type': body.jsosd_typename})

    else:
        assert('type' in body)

        if 'comment' in body and body['comment'] == 'group':
            assert(body['type'] == 'object')

            subs = reduce(add, [convertProperty(k, v) for k, v in body['properties'].items()], [])

            if 'required' in body:
                markRequiredElements(subs, body['required'])
                # Verify that the set of required elements is the same as or a
                # subset of the actual child elements (i.e. no non-existent
                # required elements).
                assert(set(body['required']) <= set(map(lambda x: x.get('name'), subs)))

            return subs

        if body['type'] == 'array':
            # Repeated element.

            assert(isinstance(body['items'], dict)) # No tuple support.

            # Delegate to convertProperty of the single child element.
            el = convertProperty(name, body['items'])
            assert(len(el) == 1) # There should be just one item.
            el = el[0]

            # Check min/max occurrences and annotate.
            el.set('minOccurs', str(body['minItems']) if 'minItems' in body else '0')
            el.set('maxOccurs', str(body['maxItems']) if 'maxItems' in body else 'unbounded')

        else:
            typ = convertType(body)
            if isinstance(typ, str):
                el = El('xs:element',
                        {'name': name, 'type': typ})
            else:
                el = El('xs:element',
                        {'name': name},
                        typ)

    # Set min/max occurrences, if unset.
    if el.get('minOccurs') is not None and el.get('maxOccurs') is None:
        el.set('maxOccurs', 'unbounded')
    if el.get('minOccurs') is None:
        el.set('minOccurs', '0')
    if el.get('maxOccurs') is None:
        el.set('maxOccurs', '1')

    return [el]


def builtinTypes():
    # XXX What to do with 'date' types?
    return {'string':  'xs:string',
            'integer': 'xs:integer',
            'number':  'xs:decimal',
            'uri':     'xs:anyURI'}

if __name__ == '__main__':
    # Parse arguments, choose input / output handles {{{

    argparse = ArgumentParser(description=
            """Converts JSON schema into a Yoda metadata XSD and XML form elements.

               Unless specified otherwise with arguments, this will accept JSON on stdin
               and output XSD on stdout.
            """
            )
    argparse.add_argument('-o', '--output')
    argparse.add_argument('input', nargs='?')
    args = argparse.parse_args()

    file_in  = sys.stdin  if args.input  is None else open(args.input)
    file_out = sys.stdout if args.output is None else open(args.output, 'w')

    # }}}

    # Parse and preprocess the JSON schema document, resolving all references.

    j = flattenSchema(annotateTypes(json.load(file_in, object_pairs_hook=OrderedDict)),
                      'default.json')
    #print(json.dumps(j, indent=2))
    #sys.exit(0)

    # Sanity check.
    assert('type'       in j and j['type'] == 'object')
    assert('properties' in j and isinstance(j['properties'], dict))

    # Generate the toplevel XML schema element.

    root = ET.fromstring('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"'
                         + ' elementFormDefault="qualified"></xs:schema>')

    # Generate toplevel type declaration elements.

    #for t in (convertType(k, v) for k, v in getTypes(j).items()):
    #    root.append(t)

    # Convert and insert all fields into the XSD.

    root.append(El('xs:element',
                   {'name': 'metadata'},
                   El('xs:complexType', {},
                      El('xs:sequence', {},
                         *reduce(add, (convertProperty(k, v)
                                       for k, v in j['properties'].items()),
                                 [])))))

    for t in (convertType(v, k) for k, v in getTypes(j).items()):
        root.append(t)

    # Print the generated XML document.

    print('<?xml version="1.0" encoding="utf-8"?>', file=file_out)
    print(ET.tostring(root, encoding='unicode'),    file=file_out)
