import yaml
import os

from cekit.descriptor import Descriptor
from cekit.errors import CekitError

osbs_schema = [yaml.safe_load("""
map:
  repository:
    map:
      name: {type: str}
      branch: {type: str}
  configuration: {type: any}
""")]

configuration_schema = [yaml.safe_load("""
    map:
      container: {type: any}
      container_file: {type: str}
""")]


class Osbs(Descriptor):
    """Object Representing OSBS configuration

    Args:
      descriptor - yaml containing Osbs object
    """
    def __init__(self, descriptor):
        self.schemas = osbs_schema
        super(Osbs, self).__init__(descriptor)

        if 'configuration' in self:
            self['configuration'] = Configuration(self['configuration'])


class Configuration(Descriptor):
    """Internal object represeting OSBS configuration subObject

    Args:
      descriptor - yaml contianing OSBS configuration"""

    def __init__(self, descriptor):
        self.schemas = configuration_schema
        super(Configuration, self).__init__(descriptor)
        self.skip_merging = ['container', 'container_file']

    def _prepare_configuration(self):
        if 'container' in self and 'container_file' in self:
            raise CekitError('You cannot specify container and container_file together!')

        if 'container_file' in self:
            if not os.path.exists(self['container_file']):
                raise CekitError("'%s' file not found!" % self['container_file'])
            with open(self['container_file'], 'r') as file_:
                self['container'] = yaml.safe_load(file_)
            del self['container_file']
