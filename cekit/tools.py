import logging
import os
import shutil
import sys
import yaml

from cekit.errors import CekitError

logger = logging.getLogger('cekit')


def cleanup(target):
    """ Prepates target/image directory to be regenerated."""
    dirs_to_clean = [os.path.join(target, 'image', 'modules'),
                     os.path.join(target, 'image', 'repos'),
                     os.path.join(target, 'repo')]
    for d in dirs_to_clean:
        if os.path.exists(d):
            logger.debug("Removing dirty directory: '%s'" % d)
            shutil.rmtree(d)


def load_descriptor(descriptor):
    """ parses descriptor and validate it against requested schema type

    Args:
      descriptor - yaml descriptor or path to a descriptor to be loaded

    Returns descriptor as a dictionary
    """
    if not os.path.exists(descriptor):
        logger.debug("Descriptor path '%s' doesn't exists, trying to parse it directly."
                     % descriptor)
        try:
            return yaml.safe_load(descriptor)
        except Exception as ex:
            raise CekitError('Cannot load descriptor.', ex)

    logger.debug("Loading descriptor from path '%s'." % descriptor)

    with open(descriptor, 'r') as fh:
        return yaml.safe_load(fh)


def decision(question):
    """Asks user for a question returning True/False answed"""
    if sys.version_info[0] < 3:
        if raw_input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
            return True
    else:
        if input("\n%s [Y/n] " % question) in ["", "y", "Y"]:
            return True

    return False
