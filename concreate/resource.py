
import hashlib
import logging
import os
import requests
try:
    import urllib.parse as urlparse
except:
    import urlparse
import shutil
import subprocess

from concreate import tools
from concreate.errors import ConcreateError

logger = logging.getLogger('concreate')


class Resource(object):
    SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha1', 'md5']
    CHECK_INTEGRITY = True

    @staticmethod
    def new(resource, base_dir=os.getcwd()):
        if 'git' in resource:
            return GitResource(resource)
        elif 'path' in resource:
            directory = resource['path']
            if not os.path.isabs(directory):
                resource['path'] = os.path.join(base_dir, directory)
            return PathResource(resource)
        elif 'url' in resource:
            return UrlResource(resource)
        raise ValueError("Resource type is not supported: %s" (resource))

    def __init__(self, descriptor):
        self.name = descriptor['name']
        if 'description' in descriptor:
            self.desription = descriptor['description']
        self.checksums = {}
        for algorithm in self.SUPPORTED_HASH_ALGORITHMS:
            if algorithm in descriptor:
                self.checksums[algorithm] = descriptor[algorithm]

    def _copy_impl(self, target):
        raise NotImplementedError("Implement _copy_impl() for Resource: "
                                  + self.__module__ + "."
                                  + type(self).__name__)

    def target_file_name(self):
        return os.path.basename(self.name)

    def copy(self, target_dir=os.getcwd()):
        target = os.path.join(target_dir, self.target_file_name())
        logger.debug("Fetching resource '%s'" % (self.name))

        overwrite = False
        if os.path.exists(target):
            try:
                self.__verify(target)
            except:
                logger.debug("Local resource verification failed")
                overwrite = True

        if os.path.exists(target) and not overwrite:
            logger.debug(
                "Local resource '%s' exists and is valid, skipping" % self.name)
            return target

        try:
            self._copy_impl(target)
        except Exception as ex:
            # exception is fatal we be logged before Concreate dies
            raise ConcreateError('Error copying resource: %s' % (self.name),
                                 ex)

        self.__verify(target)

        return target

    def __verify(self, target):
        """ Checks all defined check_sums for an aritfact """
        if not self.checksums:
            return True
        if not Resource.CHECK_INTEGRITY:
            logger.info("Integrity checking disabled, skipping verification.")
            return True
        if os.path.isdir(target):
            logger.info("Target is directory, cannot verify checksum.")
            return True
        for algorithm, checksum in self.checksums.items():
            self.__check_sum(target, algorithm, checksum)
        return True

    def __check_sum(self, target, algorithm, expected):
        """ Check that file chksum is correct
        Args:
          alg - algorithm which will be used for diget
          expected_chksum - checksum which artifact must mathc
        """

        logger.debug("Checking '%s' %s hash..." % (self.name, algorithm))

        hash_function = getattr(hashlib, algorithm)()

        with open(target, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_function.update(chunk)
        checksum = hash_function.hexdigest()

        if checksum.lower() != expected.lower():
            raise ConcreateError("The %s computed for the '%s' file ('%s') doesn't match the '%s' value"  # noqa: E501
                                 % (algorithm, self.name, checksum, expected))

        logger.debug("Hash is correct.")

    def __substitute_cache_url(self, url):
        cache = tools.cfg.get('common', {}).get('cache_url', None)
        if not cache:
            return url

        for algorithm in self.SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self.checksums:
                logger.debug("Using %s to fetch artifacts from cacher."
                             % algorithm)
                return (cache.replace('#filename#', self.name)
                        .replace('#algorithm#', algorithm)
                        .replace('#hash#', self.checksums[algorithm]))
        return url

    def _download_file(self, url, destination):
        """ Downloads a file from url and save it as destination """
        url = self.__substitute_cache_url(url)

        logger.debug("Downloading from '%s' as %s" % (url, destination))

        parsedUrl = urlparse.urlparse(url)

        if parsedUrl.scheme == 'file' or not parsedUrl.scheme:
            if os.path.isdir(parsedUrl.path):
                shutil.copytree(parsedUrl.path, destination)
            else:
                shutil.copy(parsedUrl.path, destination)
        elif parsedUrl.scheme in ['http', 'https']:
            verify = tools.cfg.get('common', {}).get('ssl_verify', True)
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


class PathResource(Resource):

    def __init__(self, descriptor):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['path'])
        super(PathResource, self).__init__(descriptor)
        self.path = descriptor['path']

    def _copy_impl(self, target):
        if not os.path.exists(self.path):
            cache = tools.cfg.get('artifact', {}).get('cache_url', None)

            # If cache_url is specified in Concreate configuration
            # file - try to fetch the 'path' artifact from cacher
            # even if it was not defined as 'url'.
            if cache:
                self._download_file(self.path, target)
                return target
            else:
                raise ConcreateError(
                    "Requested path resource: '%s' does not exist. \
                            Make sure you provided correct path." % self.path)

        if os.path.isdir(self.path):
            shutil.copytree(self.path, target)
        else:
            shutil.copy(self.path, target)
        return target


class UrlResource(Resource):

    def __init__(self, descriptor):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['url'])
        super(UrlResource, self).__init__(descriptor)
        self.url = descriptor['url'].strip()

    def _copy_impl(self, target):
        self._download_file(self.url, target)
        return target


class GitResource(Resource):

    def __init__(self, descriptor):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['git']['url'])
        super(GitResource, self).__init__(descriptor)
        self.url = descriptor['git']['url']
        self.ref = descriptor['git']['ref']

    def target_file_name(self):
        # XXX: We could make a case for using name instead of repo-ref
        return "%s-%s" % (os.path.basename(self.url), self.ref)

    def _copy_impl(self, target):
        cmd = ['git', 'clone', '--depth', '1', self.url, target, '-b',
               self.ref]
        logger.debug("Running '%s'" % ' '.join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return target
