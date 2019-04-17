import logging
import os
import platform
import subprocess

import yaml

from cekit.config import Config
from cekit.errors import CekitError
from cekit.generator.base import Generator

logger = logging.getLogger('cekit')
config = Config()


class DockerGenerator(Generator):

    ODCS_HIDDEN_REPOS_FLAG = 'include_unpublished_pulp_repos'

    def __init__(self, descriptor_path, target, overrides):
        super(DockerGenerator, self).__init__(descriptor_path, target, overrides)
        self._fetch_repos = True

    @staticmethod
    def dependencies():
        deps = {}

        if config.get('common', 'redhat'):
            deps['odcs-client'] = {
                'package': 'odcs-client',
                'executable': '/usr/bin/odcs'
            }

            deps['brew'] = {
                'package': 'brewkoji',
                'executable': '/usr/bin/brew'
            }

        return deps

    def _prepare_content_sets(self, content_sets):
        if not content_sets:
            return False

        if not config.get('common', 'redhat'):
            return False

        arch = platform.machine()

        if arch not in content_sets:
            raise CekitError("There are no content_sets defined for platform '{}'!".format(arch))

        repos = ' '.join(content_sets[arch])

        try:
            # ideally this will be API for ODCS, but there is no python3 package for ODCS
            cmd = ['/usr/bin/odcs']

            if config.get('common', 'redhat'):
                cmd.append('--redhat')

            cmd.append('create')

            compose = self.image.get('osbs', {}).get(
                'configuration', {}).get('container', {}).get('compose', {})

            if compose.get(DockerGenerator.ODCS_HIDDEN_REPOS_FLAG, False):
                cmd.extend(['--flag', DockerGenerator.ODCS_HIDDEN_REPOS_FLAG])

            cmd.extend(['pulp', repos])

            logger.debug("Creating ODCS content set via '%s'" % " ".join(cmd))

            output = subprocess.check_output(cmd).decode()
            normalized_output = '\n'.join(output.replace(" u'", " '")
                                          .replace(' u"', ' "')
                                          .split('\n')[1:])

            odcs_result = yaml.safe_load(normalized_output)

            if odcs_result['state'] != 2:
                raise CekitError("Cannot create content set: '%s'"
                                 % odcs_result['state_reason'])

            repo_url = odcs_result['result_repofile']
            return repo_url

        except CekitError as ex:
            raise ex
        except OSError as ex:
            raise CekitError("ODCS is not installed, please install 'odcs-client' package")
        except subprocess.CalledProcessError as ex:
            raise CekitError("Cannot create content set: '%s'" % ex.output)
        except Exception as ex:
            raise CekitError('Cannot create content set!', ex)

    def _prepare_repository_rpm(self, repo):
        # no special handling is needed here, everything is in template
        pass

    def prepare_artifacts(self):
        """Goes through artifacts section of image descriptor
        and fetches all of them
        """
        if not self.image.all_artifacts:
            logger.debug("No artifacts to fetch")
            return

        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')

        for artifact in self.image.all_artifacts:
            artifact.copy(target_dir)

        logger.debug("Artifacts handled")
