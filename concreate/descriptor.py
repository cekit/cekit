import hashlib
import logging
import shutil
import subprocess
import os

from concreate import DEFAULT_USER, tools
from concreate.errors import ConcreateError
from concreate.version import schema_version

logger = logging.getLogger('concreate')


class Descriptor(object):
    """ Representes a module/image descriptor
    Args:
      descriptor_path - a path to the image/module descriptor
      descriptor_type - a type of descriptor (image/module)
    """

    def __init__(self, descriptor_path, descriptor_type):
        self.directory = os.path.dirname(descriptor_path)
        self.descriptor = tools.load_descriptor(descriptor_path,
                                                descriptor_type)
        if descriptor_type == 'image':
            self.check_schema_version()

    def check_schema_version(self):
        """ Check supported schema version """
        if self.descriptor['schema_version'] != schema_version:
            raise ConcreateError("Schema version: '%s' is not supported by current version."
                                 " This version supports schema version: '%s' only."
                                 " To build this image please install concreate version: '%s'"
                                 % (self.descriptor['schema_version'],
                                    schema_version,
                                    self.descriptor['schema_version']))

    def __getitem__(self, key):
        return self.descriptor[key]

    def __setitem__(self, key, item):
        self.descriptor[key] = item

    def __iter__(self):
        return self.descriptor.__iter__()

    def items(self):
        return self.descriptor.items()

    def label(self, key):
        for l in self.descriptor['labels']:
            if l['name'] == key:
                return l
        return None

    def process(self):
        """ Prepare descriptor to be used by generating defaults """
        if 'artifacts' in self.descriptor:
            self._process_artifacts()
        if 'execute' in self.descriptor:
            self._process_execute()
        if 'ports' in self.descriptor:
            self._process_ports()
        if 'dependencies' in self.descriptor:
            self._process_dependencies()
        self._process_run()
        self._process_labels()
        return self

    def merge(self, descriptor):
        """ Merges two descriptors in a way, that arrays are appended
        and duplicit values are kept

        Args:
          descriptor - a concreate descritor
        """
        try:
            self.descriptor = tools.merge_dictionaries(self.descriptor, descriptor)
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise ConcreateError("Dictionary is missing 'name' keyword")

    def _process_artifacts(self):
        """ Processes descriptor artifacts section and generate default
        value 'name' for each artifact which doesnt have 'name' specified.
        """
        artifacts = {}
        for artifact in self.descriptor['artifacts']:
            resource = Resource.new(artifact, self.directory)
            artifacts[resource.name] = resource
        self.descriptor['artifacts'] = artifacts

    def _process_execute(self):
        """ Prepares executables of modules to contian all needed data like,
        directories, module name, unique name
        """
        for execute in self.descriptor['execute']:
            module = self.descriptor['name']
            execute['directory'] = module
            execute['name'] = "%s-%s" % (module,
                                         execute['execute'])
            if 'user' not in execute:
                execute['user'] = DEFAULT_USER

    def _process_run(self):
        """ Make sure the user is set for cmd/entrypoint  """

        if 'run' not in self.descriptor:
            self.descriptor['run'] = {}

        if 'user' not in self.descriptor['run']:
            self.descriptor['run']['user'] = DEFAULT_USER

    def _process_ports(self):
        """ Generate name attribute for ports """
        for port in self.descriptor['ports']:
            port['name'] = port['value']

    def _process_dependencies(self):
        """ Generate name attribute for dependencies """
        dependencies = {}
        for dependency in self.descriptor['dependencies']:
            resource = Resource.new(dependency, self.directory)
            dependencies[resource.name] = resource
        self.descriptor['dependencies'] = dependencies

    def _process_labels(self):
        """ Generate labels from concreate keys """
        if "labels" not in self.descriptor:
            self.descriptor['labels'] = []

        # The description key available in image descriptor's
        # root is added as labels to the image
        key = 'description'

        # If we define the label in the image descriptor
        # we should *not* override it with value from
        # the root's key
        if key in self.descriptor and not self.label(key):
            value = self.descriptor[key]
            self.descriptor['labels'].append({'name': key, 'value': value})

        # Last - if there is no 'summary' label added to image descriptor
        # we should use the value of the 'description' key and create
        # a 'summary' label with it's content. If there is even that
        # key missing - we should not add anything.
        description = self.label('description')

        if not self.label('summary') and description:
            self.descriptor['labels'].append(
                {'name': 'summary', 'value': description['value']})


class Resource(object):
    SUPPORTED_HASH_ALGORITHMS = ['sha256', 'sha1', 'md5']
    CHECK_INTEGRITY = True

    @staticmethod
    def new(resource, base_dir=os.getcwd()):
        if 'git' in resource:
            return GitResource(resource)
        elif 'file' in resource:
            directory = resource['file']
            if not os.path.isabs(directory):
                resource['file'] = os.path.join(base_dir, directory)
            return FileResource(resource)
        elif 'url' in resource:
            return UrlResource(resource)
        raise ValueError("Resource type is not supported: %s" (resource))

    def __init__(self, descriptor):
        self.name = descriptor['name']
        if 'description' in descriptor:
            self.desription = descriptor['description']
        self.checksums = {}
        for algorithm in Resource.SUPPORTED_HASH_ALGORITHMS:
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

        overwrite = False
        if os.path.exists(target):
            try:
                self.__verify(target)
            except:
                overwrite = True

        if os.path.exists(target) and not overwrite:
            logger.debug("Resource '%s' exists, skipping" % self.name)
            return target

        try:
            self._copy_impl(target)
        except Exception as ex:
            # exception is fatal we be logged before Concreate dies
            raise ConcreateError('Error copying Resource: %s' % (self.name),
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


class FileResource(Resource):
    def __init__(self, descriptor):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['file'])
        super(FileResource, self).__init__(descriptor)
        self.file = descriptor['file']

    def _copy_impl(self, target):
        if (os.path.isdir(self.file)):
            shutil.copytree(self.file, target)
        else:
            shutil.copy(self.file, target)
        return target


class UrlResource(Resource):
    def __init__(self, descriptor):
        if 'name' not in descriptor:
            descriptor['name'] = os.path.basename(descriptor['url'])
        super(UrlResource, self).__init__(descriptor)
        self.url = descriptor['url']

    def _copy_impl(self, target):
        tools.download_file(self.__substitute_cache_url(), target)
        return target

    def __substitute_cache_url(self):
        # XXX: maybe put this in [common]
        cache = tools.cfg.get('artifact', {}).get('cache_url', None)
        if not cache:
            return self.url

        for algorithm in Resource.SUPPORTED_HASH_ALGORITHMS:
            if algorithm in self.checksums:
                logger.debug("Using %s to fetch artifacts from cacher."
                             % algorithm)
                return (cache.replace('#filename#', self.name)
                        .replace('#algorithm#', algorithm)
                        .replace('#hash#', self.checksums[algorithm]))
        return self.url


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


