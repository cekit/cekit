import os
import logging
import yaml

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
  repository: {type: str, required: True}
  state: {type: str}
  filename: {type: str}
  __schema : {type: str}
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
            descriptor = self._convert_to_v2(descriptor)

        self.schemas = [repository_schema]
        super(Repository, self).__init__(descriptor)

        if 'state' not in self._descriptor:
            self._descriptor['state'] = 'enabled'
        if 'filename' not in self._descriptor:
            self._descriptor['filename'] = self._descriptor['repository'] + '.repo'
        if '__schema' not in self._descriptor:
            self._descriptor['__schema'] = 'v2'

    def _convert_to_v2(self, repository):
        descriptor = {}
        descriptor['name'] = repository
        descriptor['repository'] = repository
        descriptor['state'] = 'enabled'
        descriptor['filename'] = '%s.repo' % repository
        descriptor['__schema'] = 'v1'
        return descriptor

    def fetch(self, target_dir):
        if not os.path.exists(target_dir):
                os.makedirs(target_dir)
        Resource({'url': self._descriptor['url']}).copy(os.path.join(target_dir,
                                                                     self._descriptor['filename']))
