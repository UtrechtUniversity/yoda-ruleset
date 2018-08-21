#!/usr/bin/env python3

import json
import sys
import xml.etree.cElementTree as ET

from urllib.parse import urlparse, urljoin
from collections  import OrderedDict
from copy         import deepcopy
from functools    import reduce
from operator     import add

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

def convertTypeDeclaration(k, v):
    # TODO: Only supports some string types for now.
    return El('xs:simpleType',
              {'name': k},
              El('xs:restriction',
                 {'base': 'xs:'+v['type']},
                 El('xs:maxLength',
                    {'value': str(v['maxLength'])})))

def builtinTypes():
    # XXX Where are the xs:date and URI types?
    return {'string':  'xs:string',
            'integer': 'xs:integer',
            'number':  'xs:decimal'}

def convertElement(context, k, v):
    # Skip the 'group' level.
    if 'comment' in v and v['comment'] == 'group':
        # Return a list of all converted child elements.
        return reduce(add, [convertElement(context, k, v)
                            for k, v in v['properties'].items()])

    el = El('xs:element', {'name': k})

    if 'jsosd_typename' in dir(v):
        # Type is only a reference, this one is easy.
        # Set the type attr and move on.
        el.set('type', v.jsosd_typename)

    elif 'yoda:structure' in v:
        # Compound or subproperties.
        # Handle required elements and embed each child element.

        assert(v['yoda:structure'] in ('compound', 'subproperties'))

        subs = reduce(add, [convertElement(context, k, v) for k, v in v['properties'].items()])

        # Annotate requiredness.
        if 'required' in v:
            for child in filter(lambda x: x.get('name') in v['required'], subs):
                child.set('minOccurs', '1')

        # Insert child elements.
        el.append(El('xs:complexType', {},
                     El('xs:sequence', {},
                        *subs)))

    elif v['type'] == 'array':
        # Repeated element.

        assert(isinstance(v['items'], dict)) # No tuple support.

        # Delegate to convertElement of the single child element.
        el = convertElement(context, k, v['items'])
        assert(len(el) == 1) # There should be just one item.
        el = el[0]

        # Check min/max occurrences and annotate.
        el.set('minOccurs', str(v['minItems']) if 'minItems' in v else '0')
        el.set('maxOccurs', str(v['maxItems']) if 'maxItems' in v else 'unbounded')

    elif 'enum' in v:
        # Type should be string, or the like.
        assert(v['type'] in builtinTypes())
        el.append(El('xs:simpleType', {},
                     El('xs:restriction', {'base': builtinTypes()[v['type']]},
                        # Turn the possible enum values into xs:enumeration tags.
                        *map(lambda val: El('xs:enumeration', {'value': val}),
                             v['enum']))))

    elif v['type'] in builtinTypes():
        # Simple builtin type.
        el.set('type', builtinTypes()[v['type']])

    else:
        # Unknown type (maybe defined inline here?)
        print('paniek: ' + k)
        sys.exit(1)

    # Set min/max occurrences, if unset
    if el.get('minOccurs') is None:
        el.set('minOccurs', '0')
    if el.get('maxOccurs') is None:
        el.set('maxOccurs', '1')

    # Return the one generated element.
    # (only in the case of 'group' objects do we return more than one element)
    return [el]

if __name__ == '__main__':
    fhout = sys.stdout

    if len(sys.argv) == 2:
        fhin = open(sys.argv[1])
    elif len(sys.argv) == 1:
        fhin = sys.stdin
    else:
        print('usage: %s [schema.json]' % sys.argv[0])
        sys.exit(1)

    j = flattenSchema(annotateTypes(json.load(fhin, object_pairs_hook=OrderedDict)),
                      'default.json')

    root = ET.fromstring('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified"></xs:schema>')

    #print(json.dumps(j, indent=2))
    #sys.exit(0)

    for t in (convertTypeDeclaration(k, v) for k, v in getTypes(j).items()):
        root.append(t)

    assert('type'       in j and j['type'] == 'object')
    assert('properties' in j and isinstance(j['properties'], dict))

    root.append(El('xs:element',
                   {'name': 'metadata'},
                   El('xs:complexType', {},
                      El('xs:sequence', {},
                         *reduce(add, (convertElement(None, k, v)
                                       for k, v in j['properties'].items()))))))

    print('<?xml version="1.0" encoding="utf-8"?>', file=fhout)
    print(ET.tostring(root, encoding='unicode'), file=fhout)
