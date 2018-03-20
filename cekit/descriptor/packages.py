import os
import logging
import yaml
import subprocess

from cekit import tools
from cekit.descriptor import Descriptor, Resource
from cekit.errors import CekitError

logger = logging.getLogger('cekit')

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
        url = self._create_content_set(name)
        descriptor = {'name': name,
                      'url': url,
                      'filename': os.path.basename(url),
                      }
        super(Repository, self).__init__(descriptor)

    def _create_content_set(self, name):
        """Create pulp content set in ODCS and returns its url

        Args:
          name - name of the ODCS pulp"""
        try:
            # idealy this will be API for ODCS, but there is no python3 package for ODCS
            cmd = ['odcs', '--redhat', 'create', 'pulp', name]
            logger.debug("Creating ODCS content set via '%s'" % cmd)
            output = subprocess.check_output(cmd)
            normalized_output = '\n'.join(output.replace(" u'", " '").split('\n')[1:])
            odcs_resp = yaml.safe_load(normalized_output)
            return odcs_resp['result_repofile']
        except Exception as ex:
            raise CekitError('Cannot create content set!', ex)

    def fetch(self, target_dir):
        """Fetches repository file to the location. URL for fetching is derived from the
        [repositories] section of cekit config file

        Args:
          target_dir - a target where file is fetched to
        """

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        Resource({'url': self._descriptor['url']}).copy(target_dir)
