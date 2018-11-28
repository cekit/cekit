import logging
import os
import platform
import subprocess
import yaml

from cekit.cache.artifact import ArtifactCache
from cekit.config import Config
from cekit.errors import CekitError
from cekit.generator.base import Generator
from cekit.descriptor.resource import _PlainResource
from cekit.tools import get_brew_url


logger = logging.getLogger('cekit')
config = Config()


class DockerGenerator(Generator):

    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._params = params
        super(DockerGenerator, self).__init__(descriptor_path, target, builder, overrides, params)
        self._fetch_repos = True

    def _prepare_content_sets(self, content_sets):
        if not config.cfg['common']['redhat']:
            return False

        arch = platform.machine()
        if arch not in content_sets:
            raise CekitError("There are no contet_sets defined for platform '%s'!")

        repos = ' '.join(content_sets[arch])

        try:
            # idealy this will be API for ODCS, but there is no python3 package for ODCS
            cmd = ['odcs']

            if self._params.get('redhat', False):
                cmd.append('--redhat')
            cmd.extend(['create', 'pulp', repos])

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
        if 'artifacts' not in self.image:
            logger.debug("No artifacts to fetch")
            return

        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')

        for artifact in self.image['artifacts']:
            artifact_cache = ArtifactCache()
            if isinstance(artifact, _PlainResource):
                if artifact_cache.is_cached(artifact):
                    pass
                elif not artifact_cache.is_cached(artifact) and \
                     config.get('common', 'redhat'):
                    artifact.url = get_brew_url(artifact['md5'])
                else:
                    if 'description' in artifact:
                        logger.error("Cannot fetch Artifact: '%s', %s" % (artifact['name'],
                                                                          artifact['description']))
                    raise CekitError("Cannot fetch Artifact: '%s', please cache it via cekit-cache."
                                     % artifact['name'])

            artifact.copy(target_dir)

        logger.debug("Artifacts handled")
