try:
    import ConfigParser as configparser
except:
    import configparser
import logging
import os
import shutil
import requests
try:
    import urllib.parse as urlparse
except:
    import urlparse
import yaml
from pykwalify.core import Core

from concreate.errors import ConcreateError


SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha1', 'md5']
logger = logging.getLogger('concreate')

cfg = {}


def parse_cfg():
    cp = configparser.ConfigParser()
    cp.read(os.path.expanduser('~/.concreate'))
    return cp._sections


def download_file(url, destination):
    """ Downloads a file from url and save it as destination """
    logger.debug("Fetching '%s' as %s" % (url, destination))

    parsedUrl = urlparse.urlparse(url)

    if parsedUrl.scheme == 'file' or not parsedUrl.scheme:
        if os.path.isdir(parsedUrl.path):
            shutil.copytree(parsedUrl.path, destination)
        else:
            shutil.copy(parsedUrl.path, destination)
    elif parsedUrl.scheme == 'http' or parsedUrl.scheme == 'https':
        verify = cfg.get('common', {}).get('ssl_verify', True)
        if str(verify).lower() == 'false':
            verify = False

        res = requests.get(url, verify=verify, stream=True)
        if res.status_code != 200:
            raise ConcreateError("Could not download file from %s" % url)
        with open(destination, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
    else:
        raise ConcreateError("Unsupported URL scheme: %s" % (url))

def prepare_external_repositories(image_dir):
    """ Fetch repository definitions from provided urls """
    added_repos = []
    repo_file_urls = cfg.get('repository', {}).get('urls', None)
    if not repo_file_urls:
        return added_repos

    target_dir = os.path.join(image_dir, 'repos')
    os.makedirs(target_dir)

    for url in repo_file_urls.split(','):
        url = url.strip()
        download_file(url, os.path.join(target_dir,
                                        os.path.basename(url)))
        added_repos.append(os.path.splitext(os.path.basename(url))[0])
    return added_repos


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
    schema_name = '%s_schema.yaml' % schema_type
    schema_path = os.path.join(os.path.dirname(__file__),
                               'schema',
                               schema_name)
    if not os.path.exists(schema_path):
        raise ConcreateError('Cannot locate schema for %s.' % schema_type)

    schema = {}
    with open(schema_path, 'r') as fh:
        schema = yaml.safe_load(fh)

    if not os.path.exists(descriptor_path):
        raise ConcreateError('Cannot find provided descriptor file')

    descriptor = {}
    with open(descriptor_path, 'r') as fh:
        descriptor = yaml.safe_load(fh)

    core = Core(source_data=descriptor, schema_data=schema)
    try:
        return core.validate(raise_exception=True)
    except Exception as ex:
        raise ConcreateError("Cannot validate schema: %s" % (descriptor_path),
                             ex)
