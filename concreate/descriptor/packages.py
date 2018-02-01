import os
import yaml

from concreate import tools
from concreate.descriptor import Descriptor, Resource
from concreate.errors import ConcreateError

packages_schema = [yaml.safe_load("""
map:
  repositories:
    seq:
      - {type: str}
  install:
    seq:
      - {type: str}""")]

repository_schema = [yaml.safe_load("""
map:
  name: {type: str}""")]


class Packages(Descriptor):
    """Object representing Pakcages

    Args:
      descriptor - yaml containing Packages section
    """
    def __init__(self, descriptor):
        self.schemas = packages_schema
        super(Packages, self).__init__(descriptor)
        self._prepare()

    def _prepare(self):
        self._descriptor['repositories'] = [Repository(x)
                                            for x in self._descriptor.get('repositories', [])]


class Repository(Descriptor):
    """Object representing package repository

    Args:
      name - repository name as referenced in concreate config file
    """

    def __init__(self, name):
        self.schemas = repository_schema
        descriptor = {'name': name}
        super(Repository, self).__init__(descriptor)

    def fetch(self, target_dir):
        """Fetches repository file to the location. URL for fetching is derived from the
        [repositories] section of concreate config file

        Args:
          target_dir - a target where file is fetched to
        """
        configured_repositories = tools.cfg.get('repositories', {})

        # We need to remove the custom "__name__" element before we can show
        # which repository keys are defined in the configuration
        configured_repository_names = configured_repositories.keys()

        if '__name__' in configured_repository_names:
            configured_repository_names.remove('__name__')

        if self._descriptor['name'] not in configured_repositories:
            raise ConcreateError("Package repository '%s' used in descriptor is not "
                                 "available in Concreate configuration file. "
                                 "Available repositories: %s"
                                 % (self._descriptor['name'], configured_repository_names))

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        Resource({'url': configured_repositories[self._descriptor['name']]}).copy(target_dir)
