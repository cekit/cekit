import concreate
import yaml

from concreate.descriptor import Descriptor, Label, Env, Port, Run, Modules, \
    Packages, Osbs, Volume

image_schema = yaml.safe_load("""
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


class Image(Descriptor):
    def __init__(self, descriptor, directory):
        self.directory = directory
        self.schemas = [image_schema.copy()]

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
