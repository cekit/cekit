import logging
import os
import shutil
import subprocess
import ssl
import yaml


try:
    from urllib.parse import urlparse
    from urllib.request import urlopen
except ImportError:
    from urlparse import urlparse
    from urllib2 import urlopen

from cekit.config import Config
from cekit.crypto import SUPPORTED_HASH_ALGORITHMS, check_sum
from cekit.descriptor import Descriptor
from cekit.errors import CekitError


logger = logging.getLogger('cekit')
config = Config()


class Resource(Descriptor):
    CHECK_INTEGRITY = True

    def __new__(cls, resource, **kwargs):
        if cls is Resource:
            if 'path' in resource:
                return super(Resource, cls).__new__(_PathResource)
            elif 'url' in resource:
                return super(Resource, cls).__new__(_UrlResource)
            elif 'git' in resource:
                return super(Resource, cls).__new__(_GitResource)
            elif 'md5' in resource:
                return super(Resource, cls).__new__(_PlainResource)
            raise CekitError("Resource type is not supported: %s" % resource)

    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          name: {type: str}
          git:
            map:
              url: {type: str, required: True}
              ref: {type: str}
          path: {type: str, required: False}
          url: {type: str, required: False}
          md5: {type: str}
          sha1: {type: str}
          sha256: {type: str}
          description: {type: str}
          target: {type: str}
        assert: \"val['git'] is not None or val['path'] is not None or val['url] is not None or val['md5'] is not None\"""")]
        super(Resource, self).__init__(descriptor)
        self.skip_merging = ['md5', 'sha1', 'sha256']

        # forwarded import to prevent circural imports
        from cekit.cache.artifact import ArtifactCache
        self.cache = ArtifactCache()

        self.name = descriptor['name']

        self.description = None
        if 'description' in descriptor:
            self.description = descriptor['description']

    def __eq__(self, other):
        # All subclasses of Resource are considered same object type
        if isinstance(other, Resource):
            return self['name'] == other['name']
        return NotImplemented

    def __ne__(self, other):
        # All subclasses of Resource are considered same object type
        if isinstance(other, Resource):
            return not self['name'] == other['name']
        return NotImplemented

    def _copy_impl(self, target):
        raise NotImplementedError("Implement _copy_impl() for Resource: " +
                                  self.__module__ + "." +
                                  type(self).__name__)

    def target_file_name(self):
        if 'target' not in self:
            self['target'] = os.path.basename(self.name)
        return self['target']

    def copy(self, target=os.getcwd()):
        if os.path.isdir(target):
            target = os.path.join(target, self.target_file_name())

        logger.debug("Preparing resource '%s'" % (self.name))

        if os.path.exists(target) and self.__verify(target):
            logger.debug("Local resource '%s' exists and is valid, skipping" % self.name)
            return target

        if self.cache.is_cached(self):
            cached_resource = self.cache.get(self)
            shutil.copy(cached_resource['cached_path'],
                        target)
            logger.info("Using cached artifact '%s'." % self.name)

        else:
            try:
                self.cache.add(self)
                cached_resource = self.cache.get(self)
                shutil.copy(cached_resource['cached_path'],
                            target)
                logger.info("Using cached artifact '%s'." % self.name)
            except ValueError:
                return self.guarded_copy(target)

    def guarded_copy(self, target):
        try:
            self._copy_impl(target)
        except Exception as ex:
            logger.warn("Cekit is not able to fetch resource '%s' automatically. "
                        "You can manually place required artifact as '%s'" % (self.name, target))

            if self.description:
                logger.info(self.description)

            # exception is fatal we be logged before Cekit dies
            raise CekitError("Error copying resource: '%s'. See logs for more info."
                             % self.name, ex)

        if set(SUPPORTED_HASH_ALGORITHMS).intersection(self) and \
           not self.__verify(target):
            raise CekitError('Artifact verification failed!')

        return target

    def __verify(self, target):
        """ Checks all defined check_sums for an aritfact """
        if not set(SUPPORTED_HASH_ALGORITHMS).intersection(self):
            logger.debug("Artifact '%s' lacks any checksum definition."
                         % self.name)
            return False
        if not Resource.CHECK_INTEGRITY:
            logger.info("Integrity checking disabled, skipping verification.")
            return True
        if os.path.isdir(target):
            logger.info("Target is directory, cannot verify checksum.")
            return True
        for algorithm in SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self:
                if not check_sum(target, algorithm, self[algorithm], self['name']):
                    return False
        return True

    def __substitute_cache_url(self, url):
        cache = config.get('common', 'cache_url')
        if not cache:
            return url

        for algorithm in SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self:
                logger.debug("Using %s to fetch artifacts from cacher."
                             % algorithm)
                return (cache.replace('#filename#', self.name)
                        .replace('#algorithm#', algorithm)
                        .replace('#hash#', self[algorithm]))
        return url

    def _download_file(self, url, destination, use_cache=True):
        """ Downloads a file from url and save it as destination """
        if use_cache:
            url = self.__substitute_cache_url(url)

        logger.debug("Downloading from '%s' as %s" % (url, destination))

        parsedUrl = urlparse(url)

        if parsedUrl.scheme == 'file' or not parsedUrl.scheme:
            if os.path.isdir(parsedUrl.path):
                shutil.copytree(parsedUrl.path, destination)
            else:
                shutil.copy(parsedUrl.path, destination)
        elif parsedUrl.scheme in ['http', 'https']:
            verify = config.get('common', 'ssl_verify')
            if str(verify).lower() == 'false':
                verify = False

            ctx = ssl.create_default_context()

            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            res = urlopen(url, context=ctx)

            if res.getcode() != 200:
                raise CekitError("Could not download file from %s" % url)
            with open(destination, 'wb') as f:
                while True:
                    chunk = res.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
        else:
            raise CekitError("Unsupported URL scheme: %s" % (url))


class _PathResource(Resource):

    def __init__(self, descriptor, directory, **kwargs):
        # if the path si relative its considered relative to the directory parameter
        # it defualts to CWD, but should be set for a descriptor dir if used for artifacts
        if not os.path.isabs(descriptor['path']):
            descriptor['path'] = os.path.join(directory,
                                              descriptor['path'])

        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['path'])
        super(_PathResource, self).__init__(descriptor)
        self.path = descriptor['path']

    def _copy_impl(self, target):
        if not os.path.exists(self.path):
            cache = config.get('common', 'cache_url')

            # If cache_url is specified in Cekit configuration
            # file - try to fetch the 'path' artifact from cacher
            # even if it was not defined as 'url'.
            if cache:
                try:
                    self._download_file(self.path, target)
                    return target
                except Exception as ex:
                    logger.exception(ex)
                    raise CekitError("Could not download resource '%s' from cache" % self.name)
            else:
                raise CekitError("Could not copy resource '%s', "
                                 "source path does not exist. "
                                 "Make sure you provided correct path" % self.name)

        logger.debug("Copying repository from '%s' to '%s'." % (self.path,
                                                                target))
        if os.path.isdir(self.path):
            shutil.copytree(self.path, target)
        else:
            shutil.copy(self.path, target)
        return target


class _UrlResource(Resource):

    def __init__(self, descriptor, **kwargs):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['url'])
        super(_UrlResource, self).__init__(descriptor)
        self.url = descriptor['url'].strip()

    def _copy_impl(self, target):
        try:
            self._download_file(self.url, target)
        except:
            logger.debug("Cannot hit artifact: '%s' via cacher, trying directly." % self.name)
            self._download_file(self.url, target, use_cache=False)
        return target


class _GitResource(Resource):

    def __init__(self, descriptor, **kwargs):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['git']['url'])
        super(_GitResource, self).__init__(descriptor)
        self.url = descriptor['git']['url']
        self.ref = descriptor['git']['ref']

    def target_file_name(self):
        if 'target' not in self:
            # XXX: We could make a case for using name instead of repo-ref
            self['target'] = "%s-%s" % (os.path.basename(self.url), self.ref)

        return self['target']

    def _copy_impl(self, target):
        cmd = ['git', 'clone', '--depth', '1', self.url, target, '-b',
               self.ref]
        logger.debug("Running '%s'" % ' '.join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return target


class _PlainResource(Resource):

    def __init__(self, descriptor, **kwargs):
        super(_PlainResource, self).__init__(descriptor)

    def _copy_impl(self, target):
        try:
            self._download_file(self.url, target)
        except:
            logger.debug("Cannot hit artifact: '%s' via cacher, trying directly." % self.name)
            self._download_file(self.url, target, use_cache=False)
        return target
