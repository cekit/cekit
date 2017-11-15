import concreate
import logging
import os
import yaml

from concreate.errors import ConcreateError
from pykwalify.core import Core

logger = logging.getLogger('concreate')

common_schema = yaml.safe_load("""
map:
  name: {type: str, required: True}
  version: {type: text, required: True}
  schema_version: {type: int}
  release: {type: text}
  from: {type: str}
  description: {type: text}
  labels: {type: any}
  envs:  {type: any}
  ports: {type: any}
  run: {type: any}
  artifacts: {type: any}
  modules: {type: any}
  packages: {type: any}
  osbs: {type: any}
  volumes: {type: any}""")

overrides_schema = common_schema.copy()
overrides_schema['map']['name'] = {'type': 'str'}
overrides_schema['map']['version'] = {'type': 'text'}

module_schema = overrides_schema.copy()
module_schema['map']['execute'] = {'type': 'any'}


class Descriptor(object):
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.__validate()

    def __validate(self):
        for schema in self.schemas:
            core = Core(source_data=self.descriptor,
                        schema_data=schema, allow_assertions=True)
            try:
                core.validate(raise_exception=True)
                return
            except Exception as ex:
                # We log this as debug, because we support multiple schemas
                logger.debug("Schema validation failed: %s" % ex)

        raise ConcreateError("Cannot validate schema: %s" % (self.__class__.__name__))

    def write(self, path):
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, 'w') as outfile:
            yaml.dump(self.descriptor, outfile, default_flow_style=False)

    def label(self, key):
        for l in self.descriptor['labels']:
            if l['name'] == key:
                return l
        return None

    def merge(self, descriptor):
        """ Merges two descriptors in a way, that arrays are appended
        and duplicit values are kept
        Args:
          descriptor - a concreate descritor
        """
        try:
            self.descriptor = concreate.tools.merge_dictionaries(self.descriptor, descriptor)
        except KeyError as ex:
            logger.debug(ex, exc_info=True)
            raise ConcreateError("Cannot merge descriptors, see log message for more information")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self['name'] == other['name']
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self['name'] == other['name']
        return NotImplemented

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

    def process_defaults(self):
        """Prepares default values before rendering"""
        if 'execute' in self.descriptor:
            for execute in self.descriptor['execute']:
                if 'user' not in execute:
                    execute['user'] = concreate.DEFAULT_USER

        if 'run' not in self.descriptor:
            self.descriptor['run'] = {}

        if 'user' not in self.descriptor['run']:
            self.descriptor['run']['user'] = concreate.DEFAULT_USER


class Label(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
            name: {type: str, required: True}
            value: {type: str, required: True}
            description: {type: str}
        """)]
        super(Label, self).__init__(descriptor)


class Env(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          name: {type: str, required: True}
          value: {type: any}
          example: {type: any}
          description: {type: str}""")]
        super(Env, self).__init__(descriptor)


class Port(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          value: {type: int, required: True}
          expose: {type: bool}
          description: {type: str}""")]
        super(Port, self).__init__(descriptor)
        if 'name' not in self.descriptor:
            self.descriptor['name'] = self.descriptor['value']


class Run(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          workdir: {type: str}
          user: {type: text}
          cmd:
            seq:
              - {type: str}
          entrypoint:
            seq:
              - {type: str} """)]
        super(Run, self).__init__(descriptor)
        if 'name' not in self.descriptor:
            self.descriptor['name'] = 'run'


class Volume(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          name: {type: str}
          path: {type: str, required: True}""")]
        super(Volume, self).__init__(descriptor)
        if 'name' not in self.descriptor:
            self.descriptor['name'] = os.path.basename(self.descriptor['path'])


class Osbs(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          repository:
            map:
              name: {type: str}
              branch: {type: str}""")]
        super(Osbs, self).__init__(descriptor)


class Packages(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          repositories:
            seq:
              - {type: str}
          install:
            seq:
            - {type: str}""")]

        super(Packages, self).__init__(descriptor)


class Modules(Descriptor):
    def __init__(self, descriptor):
        self.schemas = [yaml.safe_load("""
        map:
          repositories:
            seq:
              -  {type: any}
          install:
            seq:
              - map:
                  name: {type: str, required: True}
                  version: {type: str}""")]
        super(Modules, self).__init__(descriptor)
        self._prepare()

    def _prepare(self):
        self.descriptor['repositories'] = [concreate.resource.Resource.new(r)
                                           for r in self.descriptor.get('repositories', [])]


class Execute(Descriptor):
    def __init__(self, descriptor, directory):
        self.schemas = [yaml.safe_load("""
        map:
          script: {type: str}
          user: {type: text}""")]

        super(Execute, self).__init__(descriptor)

        descriptor['directory'] = directory

        if 'user' not in descriptor:
            descriptor['user'] = concreate.DEFAULT_USER

        if 'name' not in descriptor:
            descriptor['name'] = "%s/%s" % (directory,
                                            descriptor['script'])


class Image(Descriptor):
    def __init__(self, descriptor, directory):
        self.directory = directory
        self.schemas = [common_schema.copy()]

        super(Image, self).__init__(descriptor)
        self._prepare()

    def _prepare(self):
        """Updates self.descriptor with objects and prepare sane label"""

        self.descriptor['labels'] = self.descriptor.get('labels', [])
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

        self.descriptor['labels'] = [Label(x) for x in self.descriptor.get('labels', [])]
        self.descriptor['envs'] = [Env(x) for x in self.descriptor.get('envs', [])]
        self.descriptor['ports'] = [Port(x) for x in self.descriptor.get('ports', [])]
        if 'run' in self.descriptor:
            self.descriptor['run'] = Run(self.descriptor['run'])
        self.descriptor['artifacts'] = [concreate.resource.Resource.new(a)
                                        for a in self.descriptor.get('artifacts', [])]
        if 'modules' in self.descriptor:
            self.descriptor['modules'] = Modules(self.descriptor['modules'])
        if 'packages' in self.descriptor:
            self.descriptor['packages'] = Packages(self.descriptor['packages'])
        if 'osbs' in self.descriptor:
            self.descriptor['osbs'] = Osbs(self.descriptor['osbs'])
        self.descriptor['volumes'] = [Volume(x) for x in self.descriptor.get('volumes', [])]


class Overrides(Image):
    def __init__(self, descriptor):
        schema = overrides_schema.copy()
        self.schemas = [schema]
        # calling Descriptor constructor only here (we dont wat Image() to mess with schema)
        super(Image, self).__init__(descriptor)

        self._prepare()


class Module(Image):
    """Represents a module.

    Constructor arguments:
    descriptor_path: A path to module descriptor file.
    """
    def __init__(self, descriptor, path):
        schema = module_schema.copy()
        self.schemas = [schema]
        # calling Descriptor constructor only here (we dont wat Image() to mess with schema)
        super(Image, self).__init__(descriptor)

        self._prepare()
        self.path = path
        self.name = self.descriptor['name']
        self.descriptor['execute'] = [Execute(x, self.name)
                                      for x in self.descriptor.get('execute', [])]

    def fetch_dependencies(self, repo_root):
        """ Processes modules dependencies and fetches them.

        Arguments:
        repo_root: A parent directory where repositories will be cloned in
        """
        concreate.module.get_dependencies(self.descriptor, repo_root)
