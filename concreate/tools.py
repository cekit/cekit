import logging
import os
import shutil
import yaml

from concreate.errors import ConcreateError

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
