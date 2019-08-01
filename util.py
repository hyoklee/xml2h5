"""
Collection of utility functions and classes for the HDF Product Designer
Server. Usefulness to others not guaranteed.
"""

import json
import itertools
import numbers
import numpy as np
from cStringIO import StringIO
import posixpath as pp
from collections import defaultdict
from functools import partial
from uuid import uuid4
from h5py._hl.filters import guess_chunk
import string
import random


class StringStore(object):
    """Store and concatenate strings fast."""

    def __init__(self):
        # Container for storing strings...
        self._s = StringIO()

    def append(self, string):
        """Append the new ``string`` to the rest of collection.

        :arg str string: New string.
        """
        self._s.write(string)

    def dump(self):
        """Dump all the stored strings as one."""
        return self._s.getvalue()


def value_check(iter_, cond):
    """Check the values of ``iter_`` using the ``cond`` test.

    Each value of ``iter_`` will be supplied to ``cond`` for a check. The
    ``cond`` test will either stay silent (value is OK) or raise a
    ``TypeError``.

    :arg list iter_: A list of lists with arbitrary level of nesting.
    :arg func cond: A function that accepts a single (scalar) value to test.
    """
    for n in itertools.chain(iter_):
        if type(n) is list:
            value_check(n, cond)
        else:
            cond(n)


def numpy_dtype(h5type):
    """Convert HDF5 predefined datatype to NumPy dtype.

    :arg str h5type: HDF5 predefined datatype.
    :return: A NumPy dtype object.
    """
    conv_map = {
        'H5T_STD_I8': 'i1',
        'H5T_STD_U8': 'u1',
        'H5T_STD_I16': 'i2',
        'H5T_STD_U16': 'u2',
        'H5T_STD_I32': 'i4',
        'H5T_STD_U32': 'u4',
        'H5T_STD_I64': 'i8',
        'H5T_STD_U64': 'u8',
        'H5T_IEEE_F32': 'f4',
        'H5T_IEEE_F64': 'f8'
    }
    try:
        return np.dtype(conv_map[h5type[:-2]])
    except KeyError:
        raise ValueError('%s: Invalid predefined datatype' % h5type)


def value_check_factory(cls, base=None):
    """Provide the correct function for value check.

    :arg str cls: HDF5 datatype class. Currently suported: ``H5T_STRING``,
        ``H5T_INTEGER``, ``H5T_FLOAT``.
    :arg str base: The predefined datatype of the datatype class in ``cls``.
    """
    if cls == 'H5T_STRING':
        def check_string(v):
            if not isinstance(v, basestring):
                raise TypeError('%s: Value datatype error: Not a string.' % v)
        return check_string

    elif cls == 'H5T_INTEGER':
        dtype = numpy_dtype(base)
        minval = np.iinfo(dtype).min
        maxval = np.iinfo(dtype).max

        def check_integer(v):
            if not isinstance(v, numbers.Integral):
                raise TypeError('%s: Value datatype error: Not an integer.'
                                % v)
            if v < minval or v > maxval:
                raise ValueError('%s: Value out of range for %s datatype'
                                 % (v, base))

        return check_integer

    elif cls == 'H5T_FLOAT':
        dtype = numpy_dtype(base)
        minval = np.finfo(dtype).min
        maxval = np.finfo(dtype).max

        def check_real(v):
            if not isinstance(v, numbers.Real):
                raise TypeError('%s: Value datatype error: Not a float.' % v)
            if ((v < minval and not np.allclose([minval], [v], rtol=1.e-8)) or
                    (v > maxval and
                     not np.allclose([maxval], [v], rtol=1.e-8))):
                raise ValueError('%s: Value out of range for %s datatype'
                                 % (v, base))

        return check_real

    elif cls in ('H5T_VLEN', 'H5T_COMPOUND'):
        def check_pass(v):
            return

        return check_pass

    else:
        raise NotImplementedError('%s: HDF5 datatype class is not supported.'
                                  % cls)


def h5json_to_db(otype, oinfo):
    """Convert object information from HDF5/JSON to database format.

    :arg str otype: Object type.
    :arg dict oinfo: Object information converted from HDF5/JSON.
    :return: Object information in the format compatible with the database
        schema.
    :rtype: dict
    """
    dbinfo = dict()

    dbinfo['name'] = oinfo['name']
    dbinfo['description'] = oinfo.get('description', '')
    if 'uuid' in oinfo:
        dbinfo['uuid'] = oinfo['uuid']

    if otype == 'attribute':
        dbinfo['layout'] = 'N/A'
        dbinfo['rank'] = 0
        dims = {'dims': []}
        maxdims = {'maxdims': []}
        if oinfo['shape']['class'] == 'H5S_SIMPLE':
            dbinfo['rank'] = len(oinfo['shape']['dims'])
            dims['dims'] = oinfo['shape']['dims']
            maxdims['maxdims'] = oinfo['shape'].get('maxdims',
                                                    oinfo['shape']['dims'])

        data = {'value': oinfo['value']}
        misc = {'datatype': oinfo['type']}

    elif otype == 'dataset':
        dbinfo['rank'] = 0
        dims = {'dims': []}
        maxdims = {'maxdims': []}
        if oinfo['shape']['class'] == 'H5S_SIMPLE':
            dbinfo['rank'] = len(oinfo['shape']['dims'])
            dims['dims'] = oinfo['shape']['dims']
            maxdims['maxdims'] = oinfo['shape']['maxdims']
        misc = {'datatype': oinfo['type']}
        dbinfo['layout'] = oinfo['creationProperties'].get(
            'layout', {}
        ).get('class', 'H5D_CONTIGUOUS')
        if dbinfo['layout'] == 'H5D_CHUNKED':
            misc['chunks'] = oinfo['creationProperties']['layout']['dims']
        if 'filters' in oinfo['creationProperties']:
            misc['filters'] = oinfo['creationProperties']['filters']
        if 'fillValue' in oinfo['creationProperties']:
            misc['fillValue'] = oinfo['creationProperties']['fillValue']

        if oinfo.get('value', []):
            data = {'value': oinfo['value']}
        else:
            data = {'value': {}}

    elif otype == 'group':
        dbinfo['rank'] = 0
        dbinfo['layout'] = 'N/A'
        misc = {}
        dims = {}
        maxdims = {}
        data = {"value": {}}

    else:
        raise NotImplementedError('%s: Object type not supported')

    dbinfo['misc'] = json.dumps(misc)
    dbinfo['dims'] = json.dumps(dims)
    dbinfo['maxdims'] = json.dumps(maxdims)
    dbinfo['data'] = json.dumps(data)
    dbinfo['type'] = otype

    return dbinfo


def db_to_h5json(otype, oinfo):
    """Convert object information for database format to HDF5/JSON.

    :arg str otype: Object type.
    :arg dict oinfo: Object info retrieved from the database.
    :return: Object information that can be directly converted to HDF5/JSON.
    :rtype: dict
    """
    h5j = dict()

    h5j['_objtype'] = oinfo['type']
    if 'puuid' in oinfo:
        h5j['_pid'] = oinfo['puuid']
    h5j['description'] = oinfo['description']
    h5j['id'] = oinfo['uuid']
    h5j['name'] = oinfo['name']

    if otype == 'attribute':
        h5j['creationProperties'] = {'nameCharEncoding': 'H5T_CSET_UTF8'}
        h5j['value'] = oinfo['data']['value']
        h5j['type'] = oinfo['misc']['datatype']
        if oinfo['rank'] == 0:
            h5j['shape'] = {'class': 'H5S_SCALAR'}
        else:
            if 'maxdims' not in oinfo['maxdims']:
                oinfo['maxdims']['maxdims'] = oinfo['dims']['dims']
            h5j['shape'] = {'class': 'H5S_SIMPLE',
                            'dims': oinfo['dims']['dims'],
                            'maxdims': oinfo['maxdims']['maxdims']}

    elif otype == 'dataset':
        h5j['type'] = oinfo['misc']['datatype']
        if oinfo['rank'] == 0:
            h5j['shape'] = {'class': 'H5S_SCALAR'}
        else:
            h5j['shape'] = {'class': 'H5S_SIMPLE',
                            'dims': oinfo['dims']['dims'],
                            'maxdims': oinfo['maxdims']['maxdims']}

        if len(oinfo['data']['value']):
            h5j['value'] = oinfo['data']['value']

        dcpl = dict()
        if oinfo['layout'] == 'H5D_CHUNKED':
            if 'chunks' not in oinfo['misc']:
                # For some reason, there is no chunk size for this dataset, so
                # let's calculate one...
                dims = oinfo['dims']['dims']
                maxdims = oinfo['maxdims'].get('maxdims', dims)
                # This is a hack but it is good enough as a fix for now...
                h5dtype = oinfo['misc']['datatype'].get('base',
                                                        'H5T_IEEE_F64LE')
                chunk = guess_chunk(dims, maxdims,
                                    numpy_dtype(h5dtype).itemsize)
                dcpl['layout'] = {'class': 'H5D_CHUNKED',
                                  'dims': list(chunk)}
            else:
                dcpl['layout'] = {'class': 'H5D_CHUNKED',
                                  'dims': oinfo['misc']['chunks']}
        else:
            dcpl['layout'] = {"class": oinfo['layout']}

        if 'filters' in oinfo['misc'] and len(oinfo['misc']['filters']) > 0:
            dcpl['filters'] = oinfo['misc']['filters']

        if 'fillValue' in oinfo['misc']:
            dcpl['fillValue'] = oinfo['misc']['fillValue']

        h5j['creationProperties'] = dcpl

    elif otype == 'group':
        pass

    else:
        raise NotImplementedError('%s: Object type not supported')

    return h5j


def merge_dicts(d1, d2):
    """Merge two nested dictionaries.

    :arg dict d1: First input dictionary.
    :arg dict d2: Second input dictionary.
    :return: A generator yielding the merged dictionary.
    :rtype: generator

    Example:
        >>> a = {'x': 'foo', 'y': {'bar': {1: 'abc'}, 'baz': 1000}}
        >>> b = {2: 'edf', 'y': {'baz': 'new value'}}
        >>> dict(merge_dicts(a, b))
        {2: 'edf', 'x': 'foo', 'y': {'bar': {1: 'abc'}, 'baz': 'new value'}}
    """
    for k in set(d1.keys()).union(d2.keys()):
        if k in d1 and k in d2:
            if isinstance(d1[k], dict) and isinstance(d2[k], dict):
                yield (k, dict(merge_dicts(d1[k], d2[k])))
            else:
                # Silently replace the non-dict value of the first dict with
                # the dict value from the second dict. Alternatively, raise a
                # ValueError exception.
                yield (k, d2[k])
        elif k in d1:
            yield (k, d1[k])
        else:
            yield (k, d2[k])


def check_shape(shape):
    """Validate HDF5/JSON shape information.

    :arg dict shape: Dictionary with HDF5/JSON shape information.
    """
    if 'class' in shape:
        if shape['class'] not in ('H5S_NULL', 'H5S_SCALAR', 'H5S_SIMPLE'):
            raise ValueError(
                '%s: Invalid dataspace class' % str(shape['class']))
    else:
        raise KeyError('Dataspace class missing')

    if shape['class'] == 'H5S_SIMPLE':
        if 'dims' not in shape:
            raise KeyError('Missing dataspace "dims" information')

        keys = ['dims']
        if 'maxdims' in shape:
            keys.append('maxdims')
        for k in keys:
            if type(shape[k]) is not list:
                raise TypeError('Dataspace "%s" must be a list' % k)
            rank = len(shape[k])
            if not (0 < rank <= 32):
                raise ValueError(
                    'Dataspace "%s": Invalid rank: %d' % (k, rank))

        for i, d in enumerate(shape['dims'], 1):
            if not isinstance(d, numbers.Integral):
                raise TypeError('Dataspace "dims": Dimension #%d: '
                                'Must be integer: %s' % (i, d))
            elif d < 0 or d > np.iinfo(np.uint64).max:
                raise ValueError('Dataspace "dims": Dimension #%d: '
                                 'Size out of range: %s' % (i, d))

        if 'maxdims' in shape:
            if len(shape['dims']) != len(shape['maxdims']):
                raise ValueError('Dataspace dims and maxdims not of same rank')

            for i, d in enumerate(shape['maxdims']):
                if isinstance(d, numbers.Integral):
                    if d <= 0 or d >= np.iinfo(np.uint64).max:
                        raise ValueError('Dataspace "maxdims": Dimension size '
                                         'out of range: %d' % d)
                    elif shape['dims'][i] > shape['maxdims'][i]:
                        raise ValueError('Dimension #%d: '
                                         'dims greater than maxdims' % (i + 1))
                elif isinstance(d, basestring) and d != 'H5S_UNLIMITED':
                    raise ValueError('Dataspace "maxdims": Unlimited dimension'
                                     ' size value invalid: %s' % d)

    else:
        if any([o in shape for o in ('dims', 'maxdims')]):
            raise KeyError(
                '"dims" and "maxdims" not allowed for %s dataspace'
                % str(shape['class']))


def _check_atomic_type(t):
    """Helper for validating HDF5/JSON of atomic datatypes."""
    tcls = t['class']
    if tcls == 'H5T_STRING':
        for k in ('charSet', 'length', 'strPad'):
            if k not in t:
                raise KeyError('Missing "%s" string information' % k)

        if t['charSet'] not in ('H5T_CSET_ASCII', 'H5T_CSET_UTF8'):
            raise ValueError('%s: Invalid string character set' % t['charSet'])

        if t['strPad'] not in ('H5T_STR_NULLTERM', 'H5T_STR_NULLPAD',
                               'H5T_STR_SPACEPAD'):
            raise ValueError('%s: Invalid string padding' % t['strPad'])

        if t['length'] != 'H5T_VARIABLE' and \
                not (isinstance(t['length'], numbers.Integral) and
                     t['length'] > 0):
            raise ValueError('%s: Invalid string length value' % t['length'])

    elif tcls in ('H5T_INTEGER', 'H5T_FLOAT'):
        if 'base' not in t:
            raise KeyError('H5T_FLOAT/H5T_INTEGER predefined datatype missing')
        numpy_dtype(t['base'])

    elif tcls == 'H5T_REFERENCE':
        if 'base' not in t:
            raise KeyError('Datatype reference base missing')
        elif t['base'] not in ('H5T_STD_REF_OBJ', 'H5T_STD_REF_DSETREG'):
            raise ValueError('%s: Invalid reference type' % t['base'])

    else:
        raise NotImplementedError('%s: HDF5 datatype not supported yet'
                                  % tcls)


def check_type(t):
    """Validate HDF5/JSON datatype information.

    :arg dict t: Dictionary with HDF5/JSON datatype information.
    """
    if 'class' not in t:
        raise KeyError('Datatype class missing')

    tcls = t['class']
    if tcls == 'H5T_COMPOUND':
        if 'fields' not in t:
            raise KeyError('Missing compound datatype member list')
        if type(t['fields']) is not list:
            raise TypeError('Compound datatype members must be in a list')
        if len(t['fields']) == 0:
            raise ValueError('Compound datatype must have at least one member')
        fld_names = list()
        for f in t['fields']:
            if 'name' not in f:
                raise KeyError('Missing compound member name')
            elif len(f['name']) == 0:
                raise ValueError('Empty name for a compound member')
            elif 'type' not in f:
                raise KeyError('Compound member "%s" missing datatype'
                               % f['name'])
            fld_names.append(f['name'])
            check_type(f['type'])
        for f in fld_names:
            if fld_names.count(f) > 1:
                raise ValueError('%s: Compound member name is not unique' % f)

    elif tcls == 'H5T_VLEN':
        if 'base' not in t:
            raise KeyError('H5T_VLEN datatype base missing')
        check_type(t['base'])

    elif tcls == 'H5T_ARRAY':
        if 'dims' not in t:
            raise KeyError('H5T_ARRAY dimensions missing')
        if type(t['dims']) is not list:
            raise TypeError('H5T_ARRAY dimensions must be in a list')
        if not (0 < len(t['dims']) <= 32):
            raise ValueError('Invalid H5T_ARRAY rank: %d' % len(t['dims']))
        for k, d in enumerate(t['dims']):
            if not isinstance(d, numbers.Integral):
                raise TypeError('H5T_ARRAY dimension #%d: Must be integer: %s'
                                % (k, d))
            elif d <= 0:
                raise ValueError('H5T_ARRAY dimension #%d: '
                                 'Dimension size must be positive: %s'
                                 % (k, d))
        if 'base' not in t:
            raise KeyError('H5T_ARRAY datatype base missing')
        check_type(t['base'])

    else:
        _check_atomic_type(t)


def validate_h5json(h5j, reqd=[]):
    """Validate HDF5 JSON content.

    One of these exceptions is raised on errors: KeyError, ValueError,
    TypeError, and NotImplementedError.

    :arg dict h5j: Dictionary with HDF5 JSON content describing an HDF5 object.
    :arg list reqd: An optional list of keys that are required to
        exist in ``h5j``.
    """
    if reqd:
        for k in reqd:
            if k not in h5j:
                raise KeyError('%s: Required but missing' % k)

    # Dataspace check...
    if 'shape' in h5j:
        check_shape(h5j['shape'])

    # Datatype check...
    if 'type' in h5j:
        check_type(h5j['type'])

    # Value check...
    if 'value' in h5j:
        if h5j['shape']['class'] == 'H5S_SIMPLE':
            # Value must be a list...
            if type(h5j['value']) is not list:
                raise TypeError("Value(s) must be in a list for %s dataspace"
                                % h5j['shape']['class'])
            val = h5j['value']

            # Compare declared shape with what NumPy reports for value's
            # shape...
            np_shape = np.asarray(h5j['value']).shape
            shape = tuple(h5j['shape']['dims'])
            if np_shape != shape:
                raise ValueError('Reported %s and actual %s shape mismatch'
                                 % (shape, np_shape))

        elif h5j['shape']['class'] == 'H5S_SCALAR':
            # Value cannot be a list...
            if type(h5j['value']) is list:
                raise TypeError("Value cannot be in a list for %s dataspace"
                                % h5j['shape']['class'])
            val = [h5j['value']]

        cond = value_check_factory(
            h5j['type']['class'], h5j['type'].get('base', None)
        )
        value_check(val, cond)

    # Check name...
    if 'name' in h5j:
        if not isinstance(h5j['name'], basestring):
            raise TypeError('HDF5 object name must be a string')
        elif len(h5j['name']) == 0:
            raise ValueError('HDF5 object name is an empty string')
        elif '/' in h5j['name']:
            raise ValueError('HDF5 object name contains "/" character')

    # Creation properties...
    if 'creationProperties' in h5j:
        cp = h5j['creationProperties']

        if 'nameCharEncoding' in cp:
            if cp['nameCharEncoding'] \
                    not in ('H5T_CSET_UTF8', 'H5T_CSET_ASCII'):
                raise ValueError('%s: Invalid character encoding name'
                                 % cp['nameCharEncoding'])

        # Layout...
        if 'layout' in cp:
            if 'class' not in cp['layout']:
                raise KeyError('Missing layout class')

            if cp['layout']['class'] not in ('H5D_CONTIGUOUS', 'H5D_CHUNKED',
                                             'H5D_COMPACT'):
                raise ValueError('%s: Invalid layout class'
                                 % cp['layout']['class'])

            if cp['layout']['class'] == 'H5D_CHUNKED':
                if 'dims' not in cp['layout']:
                    raise KeyError('Missing chunking dimensions')

                if type(cp['layout']['dims']) is not list:
                    raise TypeError('Chunking dimensions must be a list')

                for d in cp['layout']['dims']:
                    if not isinstance(d, numbers.Integral):
                        raise TypeError(
                            'Chunking dimension "%s" must be integer' % d
                        )
                    elif not (0 < d <= 0xffffffff):
                        raise ValueError('Chunk dimension value %d must be '
                                         'positive integer smaller than 2^32'
                                         % d)

                if np.prod(cp['layout']['dims']) > 0xffffffff:
                    raise ValueError(
                        'Number of elements in a chunk must be less than 2^32')

                if h5j['shape']['class'] == 'H5S_SIMPLE':
                    if len(h5j['shape']['dims']) != len(cp['layout']['dims']):
                        raise ValueError(
                            'Chunk rank must be same as shape rank')

                    max_dims \
                        = h5j['shape'].get('maxdims', h5j['shape']['dims'])
                    for n, d in enumerate(max_dims):
                        if isinstance(d, basestring):
                            continue
                        if d < cp['layout']['dims'][n]:
                            raise ValueError(
                                "Chunking dim size %d greater than max size %d"
                                % (cp['layout']['dims'][n], d)
                            )
                else:
                    raise ValueError('%s: This dataspace cannot be chunked'
                                     % h5j['shape']['class'])

            else:
                if 'dims' in cp['layout']:
                    raise KeyError('"dims" not allowed for layout class %s'
                                   % cp['layout']['class'])

        # Filters...
        if 'filters' in cp:
            fltrs = cp['filters']
            if type(fltrs) is not list:
                raise TypeError('Filters must be in a list')

            # Filters are allowed only for chunked layout...
            if 'layout' in cp:
                if cp['layout']['class'] != 'H5D_CHUNKED' and len(fltrs) != 0:
                    raise ValueError(
                        'Filters allowed only with chunked layout')

            for n, f in enumerate(fltrs):
                if type(f) is not dict:
                    raise TypeError('Filter #%d info not in a dict'
                                    % n)
                if 'class' not in f:
                    raise KeyError('Filter #%d class missing' % n)

                if 'id' not in f:
                    raise KeyError('Filter #%d id missing' % n)
                else:
                    if not isinstance(f['id'], numbers.Integral):
                        raise TypeError(
                            'Filter #%d id must be integer: %s' % (n, f['id'])
                        )
                    elif f['id'] <= 0:
                        raise ValueError(
                            'Filter #%d id must be positive: %d' % (n, f['id'])
                        )

                fcls = f['class']
                if fcls == 'H5Z_FILTER_DEFLATE':
                    if 'level' not in f:
                        raise KeyError('Filter #%d missing deflate level' % n)

                    if not isinstance(f['level'], numbers.Integral):
                        raise TypeError(
                            'Filter #%d deflate level must be integer: %s'
                            % (n, f['level'])
                        )
                    elif not (0 <= f['level'] <= 9):
                        raise ValueError(
                            'Filter #%d deflate level out of range: %d'
                            % (n, f['level'])
                        )

                elif fcls == 'H5Z_FILTER_FLETCHER32':
                    pass

                elif fcls == 'H5Z_FILTER_NBIT':
                    pass

                elif fcls == 'H5Z_FILTER_SCALEOFFSET':
                    if 'scaleType' not in f:
                        raise KeyError('Filter #%d missing scale type' % n)
                    elif f['scaleType'] not in ('H5Z_SO_FLOAT_DSCALE',
                                                'H5Z_SO_FLOAT_ESCALE',
                                                'H5Z_SO_INT'):
                        raise ValueError(
                            'Filter #%d invalid scale-offset filter type: %s'
                            % (n, f['scaleType']))
                    if 'scaleOffset' not in f:
                        raise KeyError('Filter #%d missing scale offset' % n)

                    if f['scaleType'] == 'H5Z_SO_INT' \
                            and h5j['type']['class'] != 'H5T_INTEGER':
                        raise ValueError(
                            '%s: Scale-offset filter type only allowed for '
                            'integer datatypes' % f['scaleType'])
                    elif f['scaleType'] == 'H5Z_SO_FLOAT_DSCALE' \
                            and h5j['type']['class'] != 'H5T_FLOAT':
                        raise ValueError(
                            '%s: Scale-offset filter type only allowed for '
                            'floating point datatypes' % f['scaleType'])
                    elif f['scaleType'] == 'H5Z_SO_FLOAT_ESCALE':
                        raise ValueError(
                            '%s: Scale-offset filter type not supported yet'
                            % f['scaleType'])

                    if not isinstance(f['scaleOffset'], numbers.Integral):
                        raise TypeError(
                            '%s: Scale offset value must be integer' % f['id'])
                    elif f['scaleOffset'] < 0:
                        raise ValueError(
                            '%d: Scale offset value cannot be negative'
                            % f['scaleOffset'])

                elif fcls == 'H5Z_FILTER_SHUFFLE':
                    pass

                elif fcls == 'H5Z_FILTER_SZIP':
                    pass

                elif fcls == 'H5Z_FILTER_USER':
                    if 'parameters' not in f:
                        raise KeyError('Filter #%d user filter missing '
                                       'parameters' % n)

                else:
                    raise ValueError('%s: Invalid filter class' % fcls)

            # Check for conflicts between specified filters...
            fltrs = [f['class'] for f in fltrs]
            if 'H5Z_FILTER_SCALEOFFSET' in fltrs \
                    and 'H5Z_FILTER_FLETCHER32' in fltrs:
                raise ValueError(
                    'Scale-offset compression filter cannot be combined with '
                    'the Fletcher32 checksum filter')

        # fillValue...
        if 'fillValue' in cp:
            cond = value_check_factory(
                h5j['type']['class'], h5j['type'].get('base', None)
            )
            value_check([cp['fillValue']], cond)


def order_objs(h5j, otype='group'):
    """Build hierarchy of HDF5 objects from design's HDF5/JSON.

    :arg dict h5j: HDF5/JSON of a design.
    :arg str otype: The type of HDF5 objects to report back. If not ``group``
        then it will be ``dataset``.
    :return: A list of dicts with
    """
    if 'root' not in h5j:
        raise KeyError('"root" key missing')
    grps = [{'id': h5j['root'], 'path': '/'}]
    dsets = []

    def _get_hard_links(gid, collection):
        links = list()
        for l in h5j['groups'][gid].get('links', []):
            if l['class'] == 'H5L_TYPE_HARD' and l['collection'] == collection:
                links.append(l)
        return links

    def tree_walker(ginfo):
        dlinks = _get_hard_links(ginfo['id'], 'datasets')
        for dl in dlinks:
            dsets.append({'id': dl['id'],
                          'path': pp.join(ginfo['path'], dl['title'])})

        glinks = _get_hard_links(ginfo['id'], 'groups')
        chld_grps = list()
        for gl in glinks:
            chld_grps.append({'id': gl['id'],
                              'path': pp.join(ginfo['path'], gl['title'])})
        grps.extend(chld_grps)
        for cg in chld_grps:
            tree_walker(cg)

    tree_walker(grps[0])

    return grps if otype == 'group' else dsets


def h5dtype_name(h5dtype):
    """Convert HDF5 predefined datatype names to commonly used ones.

    :arg dict h5dtype: HDF5/JSON of a datatype. The endianness is disregarded.
    """
    conv_map = {
        'H5T_STD_I8': 'int8',
        'H5T_STD_U8': 'uint8',
        'H5T_STD_I16': 'int16',
        'H5T_STD_U16': 'uint16',
        'H5T_STD_I32': 'int32',
        'H5T_STD_U32': 'uint32',
        'H5T_STD_I64': 'int64',
        'H5T_STD_U64': 'uint64',
        'H5T_IEEE_F32': 'float32',
        'H5T_IEEE_F64': 'float64',
        'H5T_STRING': 'string',
        'H5T_COMPOUND': 'compound',
        'H5T_ARRAY': 'array',
        'H5T_BITFIELD': 'bitfield',
        'H5T_REFERENCE': 'reference',
        'H5T_OPAQUE': 'opaque',
        'H5T_VLEN': 'vlen'
    }
    try:
        dtcls = h5dtype['class']
        if dtcls in ('H5T_FLOAT', 'H5T_INTEGER'):
            return conv_map[h5dtype['base'][:-2]]
        else:
            return conv_map[dtcls]
    except KeyError:
        raise ValueError('%s: Invalid HDF5 datatype' % h5dtype)


def is_dimscale(attrs):
    """Check if the dataset is a dimension scale.

    :arg list attrs: All dataset's attributes in HDF5/JSON.
    """
    # Check if REFERENCE_LIST attribute is present...
    ref_list = any(a['name'] == 'REFERENCE_LIST' and
                   a['type']['class'] == 'H5T_COMPOUND'
                   for a in attrs)

    # Check if CLASS attribute is present...
    cls_ = any(a['name'] == 'CLASS'and a['value'] == 'DIMENSION_SCALE'
               for a in attrs)

    if ref_list and cls_:
        return True
    else:
        return False


def is_dimlist(attrs):
    """Check if the dataset has dimension scales attached.

    :arg list attrs: All dataset's attributes in HDF5/JSON.
    """
    # Check if DIMENSION_LIST attribute is present...
    dim_list = any(a['name'] == 'DIMENSION_LIST' and
                   a['type']['class'] == 'H5T_VLEN'
                   for a in attrs)

    return True if dim_list else False


def scrub_value(val, func):
    """Clean value by applying ``func`` to it.

    :arg val: A scalar or a list of lists.
    :arg func: Function to apply to every ``val``'s value. Takes one argument.
    """
    for i, item in enumerate(val):
        if isinstance(item, list):
            scrub_value(item, func)
        else:
            val[i] = func(item)


def replace_uuid(val, new_val_src):
    """Substitute UUIDs in REFERENCE_LIST and DIMENSION_LIST attribute values.

    :arg str val: A string.
    :arg dict new_val_src: A dictionary providing the new value for ``val``.
    """
    if isinstance(val, basestring) and val.startswith('datasets/'):
        parts = val.split('/')
        parts[1] = new_val_src[parts[1]]
        return '/'.join(parts)
    return val


def substitute_uuids(objs, root_uuid):
    """Substitute UUIDs of a design's objects.

    The UUID of each object is replaced with a new one so the object becomes
    independent (detached) from its source in the database. UUIDs are expected
    to be in the ``_pid`` and ``id`` dict keys, as well as in the values of
    ``REFERENCE_LIST`` and ``DIMENSION_LIST`` attributes.

    :arg list objs: List of dicts. Each dict represents one object in the
        design. The object dicts are in the same order as output from the
        database.
    :arg str root_uuid: The root group's UUID.
    :return: New root UUID.
    :rtype: str
    """
    # Dictionary that acts both as the store and factory for old UUIDs and
    # their substitutes. Using an object's UUID as a key will either return its
    # new UUID or generate a new one at that time and store it for later use.
    sub_uuid = defaultdict(lambda: str(uuid4()))

    # Start with new UUID for the root group...
    sub_uuid[root_uuid]

    replacer = partial(replace_uuid, new_val_src=sub_uuid)

    for o in objs:
        o['id'] = sub_uuid[o['id']]
        if '_pid' in o:
            o['_pid'] = sub_uuid[o['_pid']]
        if o['_objtype'] == 'attribute' and o['name'] in ('REFERENCE_LIST',
                                                          'DIMENSION_LIST'):
            if 'value' in o:
                scrub_value(o['value'], replacer)

    return sub_uuid[root_uuid]


def random_string(nchar):
    """Produce a random string of ``nchar`` characters.

    :arg int nchar: Length of random string.
    """
    return ''.join(random.choice(string.hexdigits) for x in range(nchar))
