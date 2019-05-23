import os

import yaml

from cekit.descriptor import Descriptor
from cekit.errors import CekitError

osbs_schema = [yaml.safe_load("""
map:
  repository:
    map:
      name: {type: str}
      branch: {type: str}
  configuration: {type: any}
  extra_dir: {type: str}

""")]

configuration_schema = [yaml.safe_load("""
    map:
      container: {type: any}
      container_file: {type: str}
""")]


class Osbs(Descriptor):
    """
    Object Representing OSBS configuration

    Args:
      descriptor: dictionary object containing OSBS configuration
      descriptor_path: path to descriptor file
    """

    def __init__(self, descriptor, descriptor_path):
        self.schemas = osbs_schema
        self.descriptor_path = descriptor_path
        super(Osbs, self).__init__(descriptor)

        if 'configuration' in self:
            self['configuration'] = Configuration(self['configuration'], self.descriptor_path)

    @property
    def name(self):
        return self.get('name')

    @name.setter
    def name(self, value):
        self._descriptor['name'] = value

    @property
    def branch(self):
        return self.get('branch')

    @branch.setter
    def branch(self, value):
        self._descriptor['branch'] = value

    @property
    def configuration(self):
        return self.get('configuration')

    @property
    def extra_dir(self):
        return self.get('extra_dir')

    @extra_dir.setter
    def extra_dir(self, value):
        self._descriptor['extra_dir'] = value


class Configuration(Descriptor):
    """Internal object represeting OSBS configuration subObject

    Args:
      descriptor - yaml contianing OSBS configuration"""

    def __init__(self, descriptor, descriptor_path):
        self.schemas = configuration_schema
        self.descriptor_path = descriptor_path
        super(Configuration, self).__init__(descriptor)
        self.skip_merging = ['container', 'container_file']

        if 'container' in self and 'container_file' in self:
            raise CekitError('You cannot specify container and container_file together!')

        if 'container_file' in self:
            container_file = os.path.join(self.descriptor_path, self['container_file'])
            if not os.path.exists(container_file):
                raise CekitError("'%s' file not found!" % container_file)
            with open(container_file, 'r') as file_:
                self['container'] = yaml.safe_load(file_)
            del self['container_file']
