import os
import logging
import yaml

from cekit import tools
from cekit.errors import CekitError
from cekit.descriptor import Descriptor, Resource

logger = logging.getLogger('cekit')

packages_schema = [yaml.safe_load("""
map:
  repositories:
    seq:
      - {type: any}
  install:
    seq:
      - {type: any}""")]


repository_schema = yaml.safe_load("""
map:
  name: {type: str, required: True}
  present: {type: bool}
  url:
    map:
      repository: {type: str}
      gpg: {type: str}
  rpm: {type: str}
  odcs:
    map:
     pulp: {type: str}
  filename: {type: str}
  """)


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
      descriptor - repository name as referenced in cekit config file
    """

    def __init__(self, descriptor):
        # we test parameter is not dict asi there is no easy way how to test
        # if something is string both in py2 and py3
        if not isinstance(descriptor, dict):
            descriptor = self._create_repo_object(descriptor)

        if 'filename' not in descriptor:
            descriptor['filename'] = '%s.repo' % descriptor['name'].replace(' ', '_')
        if 'url' not in descriptor:
            descriptor['url'] = {}

        self.schemas = [repository_schema]
        super(Repository, self).__init__(descriptor)

        if 'present' not in self._descriptor:
            self._descriptor['present'] = True

    def _create_repo_object(self, repository):
        logger.warning("The way of defining repository '%s' is deprecated. Convert "
                       "it to an URL based repository object. Consult Cekit docs, "
                       "for more details." % repository)
        descriptor = {}
        descriptor['name'] = repository
        descriptor['url'] = {}
        descriptor['url']['repository'] = self._get_repo_url(descriptor)
        return descriptor

    def _get_repo_url(self, descriptor):
        """Retruns repository url from Cekit config files repositories section"""
        configured_repositories = tools.cfg.get('repositories', {})

        # We need to remove the custom "__name__" element before we can show
        # which repository keys are defined in the configuration
        configured_repository_names = configured_repositories.keys()

        if '__name__' in configured_repository_names:
            configured_repository_names.remove('__name__')

        if descriptor['name'] not in configured_repositories:
            raise CekitError("Package repository '%s' used in descriptor is not "
                             "available in Concreate configuration file. "
                             "Available repositories: %s"
                             % (descriptor['name'], configured_repository_names))

        return configured_repositories[descriptor['name']]

    def fetch(self, target_dir):
        if not os.path.exists(target_dir):
                os.makedirs(target_dir)
        Resource({'url': self._descriptor['url']['repository']}) \
            .copy(os.path.join(target_dir, self._descriptor['filename']))
