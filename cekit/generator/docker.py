import logging
import subprocess
import yaml

from cekit.errors import CekitError
from cekit.generator.base import Generator

logger = logging.getLogger('cekit')


class DockerGenerator(Generator):

    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._params = params
        super(DockerGenerator, self).__init__(descriptor_path, target, builder, overrides, params)

    def _prepare_repository_odcs_pulp(self, repo):
        """Create pulp content set in ODCS and returns its url

        Args:
          repo - repository object to generate ODCS pulp for"""
        try:
            # idealy this will be API for ODCS, but there is no python3 package for ODCS
            cmd = ['odcs']

            if self._params.get('redhat', False):
                cmd.append('--redhat')
            cmd.extend(['create', 'pulp', repo['odcs']['pulp']])

            logger.debug("Creating ODCS content set via '%s'" % cmd)

            output = subprocess.check_output(cmd)
            normalized_output = '\n'.join(output.replace(" u'", " '")
                                          .replace(' u"', ' "')
                                          .split('\n')[1:])

            odcs_result = yaml.safe_load(normalized_output)

            if odcs_result['state'] != 2:
                raise CekitError("Cannot create content set: '%s'"
                                 % odcs_result['state_reason'])

            repo_url = odcs_result['result_repofile']

            repo['url']['repository'] = repo_url

            return True

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
