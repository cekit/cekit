import logging
import os

import yaml

from cekit.descriptor import Descriptor
from cekit.errors import CekitError

osbs_schema = yaml.safe_load("""
map:
  repository: {type: any}
  configuration: {type: any}
  koji_target: {type: str}
  extra_dir: {type: str}

""")

configuration_schema = yaml.safe_load("""
    map:
      container: {type: any}
      container_file: {type: str}
""")

repository_schema = yaml.safe_load("""
    map:
      name: {type: str}
      branch: {type: str}
""")

logger = logging.getLogger('cekit')

class Osbs(Descriptor):
    """
    Object Representing OSBS configuration

    Args:
      descriptor: dictionary object containing OSBS configuration
      descriptor_path: path to descriptor file
    """

    def __init__(self, descriptor, descriptor_path):
        self.schema = osbs_schema
        self.descriptor_path = descriptor_path
        super(Osbs, self).__init__(descriptor)

        self['configuration'] = Configuration(
            self._descriptor.get('configuration', {}), self.descriptor_path)

        self['repository'] = Repository(self._descriptor.get(
            'repository', {}), self.descriptor_path)

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

    @property
    def koji_target(self):
        return self.get('koji_target')

    @koji_target.setter
    def koji_target(self, value):
        self._descriptor['koji_target'] = value

    @property
    def repository(self):
        return self.get('repository')


class Configuration(Descriptor):
    """Internal object representing OSBS configuration subObject

    Args:
      descriptor - yaml containing OSBS configuration"""

    def __init__(self, descriptor, descriptor_path):
        self.schema = configuration_schema
        self.descriptor_path = descriptor_path
        super(Configuration, self).__init__(descriptor)

        if 'container' in self and 'container_file' in self:
            raise CekitError('You cannot specify container and container_file together!')

        if 'container_file' in self:
            container_file = os.path.join(self.descriptor_path, self['container_file'])
            if not os.path.exists(container_file):
                raise CekitError("'%s' file not found!" % container_file)
            with open(container_file, 'r') as file_:
                self['container'] = yaml.safe_load(file_)
            del self['container_file']

        remote_source = self.get('container', {}).get('remote_source', {})
        if remote_source:
            logger.debug("Cachito definition is {}".format(remote_source))

class Repository(Descriptor):
    def __init__(self, descriptor, descriptor_path):
        self.schema = repository_schema
        self.descriptor_path = descriptor_path
        super(Repository, self).__init__(descriptor)
