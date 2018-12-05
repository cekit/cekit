import logging
import os
import shutil
import sys
import subprocess
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


def get_brew_url(md5):
    try:
        logger.info("Getting brew details for an artifact with '%s' md5 sum" % md5)
        list_archives_cmd = ['brew', 'call', '--json-output', 'listArchives',
                             'checksum=%s' % md5, 'type=maven']
        logger.debug("Executing '%s'." % " ".join(list_archives_cmd))
        archive = yaml.safe_load(subprocess.check_output(list_archives_cmd))[0]
        build_id = archive['build_id']
        filename = archive['filename']
        group_id = archive['group_id']
        artifact_id = archive['artifact_id']
        version = archive['version']

        get_build_cmd = ['brew', 'call', '--json-output', 'getBuild', 'buildInfo=%s' % build_id]
        logger.debug("Executing '%s'" % " ".join(get_build_cmd))
        build = yaml.safe_load(subprocess.check_output(get_build_cmd))
        package = build['package_name']
        release = build['release']

        url = 'http://download.devel.redhat.com/brewroot/packages/' + package + '/' + \
            version.replace('-', '_') + '/' + release + '/maven/' + \
            group_id.replace('.', '/') + '/' + artifact_id.replace('.', '/') + '/' + \
            version + '/' + filename
    except subprocess.CalledProcessError as ex:
        logger.error("Can't fetch artifacts details from brew: '%s'." %
                     ex.output)
        raise ex
    return url

class Chdir(object):
    """ Context manager for changing the current working directory """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)