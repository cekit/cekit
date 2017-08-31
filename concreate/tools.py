try:
    import ConfigParser as configparser
except:
    import configparser
import hashlib
import logging
import os
import shutil
import requests
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


def is_repo_url(url):
    """ Concreate assumes any absolute path is not url """
    return not url.startswith('/')


class Artifact(object):
    """A class representing artifact """
    check_integrity = True
    target_dir = ""

    def __init__(self, artifact_dict):
        self.artifact = artifact_dict['artifact']
        self.name = artifact_dict['name']
        self.sums = {}
        self.filename = os.path.join(self.target_dir, self.name)
        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in artifact_dict:
                self.sums[alg] = artifact_dict[alg]

    def _generate_url(self):
        """ Adjust url to use artifact cache if needed.
        
        It can replace:
          #filename# - replaced by a basename of file
          #algorithm# - replace by an algorithm family
          #hash# - artifact hash
        """
        cache = cfg.get('artifact', {}).get('cache_url', None)
        if not cache:
            self.url = self.artifact
            return

        for alg in SUPPORTED_HASH_ALGORITHMS:
            if alg in self.sums:
                logger.debug("Using %s to fetch artifacts from cacher." % alg)
                self.url = (cache.replace('#filename#', self.name)
                            .replace('#algorithm#', alg)
                            .replace('#hash#', self.sums[alg]))
                break

    def verify(self):
        """ Checks all defined check_sums for an aritfact """
        if not self.check_integrity:
            return True
        for algorithm, chksum in self.sums.items():
            self._check_sum(algorithm, chksum)
        return True

    def _check_sum(self, algorithm, expected_chksum):
        """ Check that file chksum is correct

        Args:
          alg - algorithm which will be used for diget
          expected_chksum - checksum which artifact must mathc
        """

        logger.debug("Checking '%s' %s hash..." % (self.name, algorithm))

        hash_function = getattr(hashlib, algorithm)()

        with open(self.filename, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_function.update(chunk)
        chksum = hash_function.hexdigest()

        if chksum.lower() != expected_chksum.lower():
            raise ConcreateError("The %s computed for the '%s' file ('%s') doesn't match the '%s' value"
                             % (algorithm, self.name, chksum, expected_chksum))

        logger.debug("Hash is correct.")

    def fetch(self):
        """ Fetches the artifact to the artifact dir """
        self._generate_url()
        destination = os.path.join(self.target_dir, self.name)
        # If the artifacts exist just return - we dont care if sum is correct here
        if os.path.exists(destination):
            logger.debug("Using fetched artifact '%s' for '%s'. " % (destination,
                                                                     self.name))
            return self
        download_file(self.url, destination)
        return self


def download_file(url, destination):
    """ Downloads a file from url and save it as destination """
    logger.debug("Fetching '%s' as %s" % (url, destination))

    verify = cfg.get('common', {}).get('ssl_verify', True)
    if str(verify).lower() == 'false':
        verify = False

    res = requests.get(url, verify=verify, stream=True)
    if res.status_code != 200:
        raise ConcreateError("Could not download file from %s" % url)
    with open(destination, 'wb') as f:
        for chunk in res.iter_content(chunk_size=1024):
            f.write(chunk)


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
        raise ConcreateError("Cannot validate schema", ex)
