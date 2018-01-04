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


def merge_descriptors(desc1, desc2):
    """
    Merges two descriptors with handling embedded lists and
    descriptors.

    Args:
      desc1, desc2: descriptors to merge

    Return merged descriptor
    """
    for k2, v2 in desc2.items():
        if k2 not in desc1:
            desc1[k2] = v2
        else:
            if isinstance(v2, list):
                desc1[k2] = merge_lists(desc1[k2], v2)
            elif isinstance(v2, Descriptor):
                desc1[k2] = merge_descriptors(desc1[k2], v2)
    return desc1


def merge_lists(list1, list2):
    """ Merges two lists handling embedded dictionaries via 'name' as a key
    In a case of simple type values are appended.

    Args:
      list1, list2 - list to merge

    Returns merged list
    """
    for v2 in list2:
        if isinstance(v2, Descriptor):
            if v2 in list1:
                merge_descriptors(list1[list1.index(v2)], v2)
            else:
                list1.append(v2)
        elif isinstance(v2, list):
            raise ConcreateError("Cannot merge list of lists")
        else:
            if v2 not in list1:
                list1.append(v2)
    return list1
