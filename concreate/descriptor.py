import logging
import os

from concreate import DEFAULT_USER, tools
from concreate.resource import Resource
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

    def get(self, k, default=None):
        return self.descriptor.get(k, default)

    def label(self, key):
        for l in self.descriptor['labels']:
            if l['name'] == key:
                return l
        return None

    def process(self):
        """ Prepare descriptor to be used by generating defaults """
        if 'execute' in self.descriptor:
            self._process_execute()
        if 'ports' in self.descriptor:
            self._process_ports()
        self._process_artifacts()
        self._process_modules()
        self._process_volumes()
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
            self.descriptor = tools.merge_dictionaries(
                self.descriptor, descriptor)
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise ConcreateError("Cannot merge descriptors, see log message for more information")

    def _process_execute(self):
        """ Prepares executables of modules to contian all needed data like,
        directories, module name, unique name
        """
        for execute in self.descriptor['execute']:
            module = self.descriptor['name']
            execute['directory'] = module
            execute['name'] = "%s-%s" % (module,
                                         execute['script'])
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

    def _process_artifacts(self):
        """ Makes sure every artifact has 'name' set """

        artifacts = self.descriptor.get('artifacts', [])

        for artifact in artifacts:
            if 'name' not in artifact:
                # This is suboptimal, but at this point we cannot reuse created
                # resource object. We do create it only to retrieve the name
                # of the artifact. We do this because we can have different types
                # of resources (path, url, etc).
                artifact['name'] = Resource.new(artifact, self.directory).name

        self.descriptor['artifacts'] = artifacts

    def _process_modules(self):
        """
        If a 'modules' directory is found next to descriptor -
        add it as a module repository.
        """
        modules = self.descriptor.get('modules', {})
        local_modules_path = os.path.join(self.directory, 'modules')

        repositories = modules.get('repositories', [])
        # If a directory called 'modules' is found next to the image descriptor
        # scan it for modules.
        if os.path.isdir(local_modules_path):
            repositories.append({'path': 'modules', 'name': 'modules'})

        for repository in repositories:
            # if the name is already there we will not change it
            if 'name' in repository:
                continue
            name = ""
            if 'git' in repository:
                name = repository['git']['url']
            elif 'path' in repository:
                name = repository['path']
            elif 'url' in repository:
                name = repository['url']
            repository['name'] = os.path.splitext(os.path.basename(name))[0]
        modules['repositories'] = repositories
        self.descriptor['modules'] = modules

    def _process_volumes(self):
        volumes = self.descriptor.get('volumes', [])

        if not volumes:
            return

        for volume in volumes:
            if 'name' not in volume:
                volume['name'] = volume.get('path')

        self.descriptor['volumes'] = volumes

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
