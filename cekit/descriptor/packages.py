import os
import yaml

from cekit import tools
from cekit.descriptor import Descriptor, Resource
from cekit.errors import CekitError

packages_schema = [yaml.safe_load("""
map:
  repositories:
    seq:
      - {type: any}
  install:
    seq:
      - {type: str}""")]

repository_schema = [yaml.safe_load("""
map:
  name: {type: str}
  url: {type: str}
  filename: {type: str}
  """)]


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
      name - repository name as referenced in cekit config file
    """

    def __init__(self, name):
        self.schemas = repository_schema

        configured_repositories = tools.cfg.get('repositories', {})
        # We need to remove the custom "__name__" element before we can show
        # which repository keys are defined in the configuration
        configured_repository_names = configured_repositories.keys()

        if '__name__' in configured_repository_names:
            configured_repository_names.remove('__name__')

        if name not in configured_repositories:
            raise CekitError("Package repository '%s' used in descriptor is not "
                                 "available in Cekit configuration file. "
                                 "Available repositories: %s"
                                 % (name, configured_repository_names))
        descriptor = {'name': name,
                      'url': configured_repositories[name],
                      'filename': os.path.basename(configured_repositories[name]),
                      }
        super(Repository, self).__init__(descriptor)

    def fetch(self, target_dir):
        """Fetches repository file to the location. URL for fetching is derived from the
        [repositories] section of cekit config file

        Args:
          target_dir - a target where file is fetched to
        """

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        Resource({'url': self._descriptor['url']}).copy(target_dir)
