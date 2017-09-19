try:
    import ConfigParser as configparser
except:
    import configparser
import logging
import os
import shutil
import yaml
from pykwalify.core import Core

from concreate.errors import ConcreateError


logger = logging.getLogger('concreate')

cfg = {}


def parse_cfg():
    cp = configparser.ConfigParser()
    cp.read(os.path.expanduser('~/.concreate'))
    return cp._sections


def cleanup(target):
    """ Prepates target/image directory to be regenerated."""
    dirs_to_clean = [os.path.join(target, 'image', 'modules'),
                     os.path.join(target, 'image', 'repos'),
                     os.path.join(target, 'repo')]
    for d in dirs_to_clean:
        if os.path.exists(d):
            logger.debug("Removing dirty directory: '%s'" % d)
            shutil.rmtree(d)


def load_descriptor(descriptor_path, schema_type):
    """ parses descriptor and validate it against requested schema type

    Args:
      schema_type - type of schema (module/image)
      descriptor_path - path to image/modules descriptor to be validated

    Returns validated schema
    """
    logger.debug("Loading %s descriptor from path '%s'."
                 % (schema_type,
                    descriptor_path))

    if not os.path.exists(descriptor_path):
        raise ConcreateError('Cannot find provided descriptor file')

    common_schema_path = os.path.join(os.path.dirname(__file__),
                                      'schema',
                                      'common.yaml')
    schema = {}

    # Read main schema definition
    with open(common_schema_path, 'r') as fh:
        schema = yaml.safe_load(fh)

    specific_schema_path = os.path.join(os.path.dirname(__file__),
                                        'schema',
                                        '%s.yaml' % schema_type)

    # Read schema definition for specific type
    with open(specific_schema_path, 'r') as fh:
        specific_schema = yaml.safe_load(fh)
        schema = merge_dictionaries(schema, specific_schema, True)

    descriptor = {}

    with open(descriptor_path, 'r') as fh:
        descriptor = yaml.safe_load(fh)

    core = Core(source_data=descriptor,
                schema_data=schema, allow_assertions=True)
    try:
        return core.validate(raise_exception=True)
    except Exception as ex:
        raise ConcreateError("Cannot validate schema: %s" % (descriptor_path),
                             ex)


def merge_dictionaries(dict1, dict2, kwalify_schema=False):
    """
    Merges two dictionaries handling embedded lists and
    dictionaries.

    In a case of simple type; values from dict1 are preserved by default, but
    if `kwalify_schema` argument is set to `True`, values from dict2 are used.

    Args:
      dict1, dict2: dictionaries to merge
      kwalify_schema: defines if we're merging schema or descriptors

    Return merged dictionaries
    """
    for k2, v2 in dict2.items():
        if k2 not in dict1:
            dict1[k2] = v2
        else:
            if isinstance(v2, list):
                dict1[k2] = merge_lists(dict1[k2], v2)
            elif isinstance(v2, dict):
                dict1[k2] = merge_dictionaries(dict1[k2], v2, kwalify_schema)
            else:
                # if the type is int or strings we override the value from
                # dict2 but only when we're merging kwalify schema, for other
                # types of merges we're interested in using the value from dict1
                if kwalify_schema:
                    dict1[k2] = v2
    return dict1


def merge_lists(list1, list2):
    """ Merges two lists handling embedded dictionaries via 'name' as a key
    In a case of simple type values are appended.

    Args:
      list1, list2 - list to merge

    Returns merged list
    """
    list1_dicts = [x for x in list1 if isinstance(x, dict)]
    for v2 in list2:
        if isinstance(v2, dict):
            if v2['name'] not in [x['name'] for x in list1_dicts]:
                list1.append(v2)
            else:
                for v1 in list1_dicts:
                    if v2['name'] == v1['name']:
                        merge_dictionaries(v1, v2)
        elif isinstance(v2, list):
            raise ConcreateError("Cannot merge list of lists")
        else:
            if v2 not in list1:
                list1.append(v2)
    return list1
