import logging
import os
import shutil
import yaml

from concreate.errors import ConcreateError
from concreate.descriptor import Descriptor

try:
    import ConfigParser as configparser
except:
    import configparser

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


def load_descriptor(descriptor_path):
    """ parses descriptor and validate it against requested schema type

    Args:
      descriptor_path - path to image/modules descriptor to be validated

    Returns descriptor as a dictionary
    """
    logger.debug("Loading descriptor from path '%s'." % descriptor_path)

    if not os.path.exists(descriptor_path):
        raise ConcreateError('Cannot find provided descriptor file')

    with open(descriptor_path, 'r') as fh:
        return yaml.safe_load(fh)


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
            elif isinstance(v2, dict) or isinstance(v2, Descriptor):
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
    list1_dicts = [x for x in list1 if isinstance(x, dict) or isinstance(x, Descriptor)]

    for v2 in list2:
        if isinstance(v2, dict) or isinstance(v2, Descriptor):
            if 'name' not in v2:
                raise KeyError("The 'name' key was not found in dict: %s" % v2)

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
