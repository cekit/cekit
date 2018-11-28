import logging
import yaml
import os

from cekit.tools import get_brew_url
from cekit.config import Config
from cekit.generator.base import Generator
from cekit.descriptor.resource import _PlainResource

logger = logging.getLogger('cekit')
config = Config()

RHEL_REPOS_MAP = {}
RHEL_REPOS_MAP['rhel-7-server-rpms'] = 'rhel-7-for-power-le-rpms'
RHEL_REPOS_MAP['rhel-7-extras-rpms'] = 'rhel-7-for-power-le-extras-rpms'
RHEL_REPOS_MAP['rhel-server-rhscl-7-rpms'] = 'rhel-7-server-for-power-le-rhscl-rpms'

class OSBSGenerator(Generator):
    def __init__(self, descriptor_path, target, builder, overrides, params):
        self._wipe = True
        super(OSBSGenerator, self).__init__(descriptor_path, target, builder, overrides, params)
        self._prepare_container_yaml()

    def _prepare_content_sets(self, content_sets):
        content_sets_f = os.path.join(self.target, 'image', 'content_sets.yml')
        with open(content_sets_f, 'w') as _file:
            yaml.safe_dump(content_sets, _file, default_flow_style=False)

    def _prepare_container_yaml(self):
        container_f = os.path.join(self.target, 'image', 'container.yaml')
        container = self.image.get('osbs', {}).get('configuration', {}).get('container')
        if not container:
            return

        with open(container_f, 'w') as _file:
            yaml.safe_dump(container, _file, default_flow_style=False)

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
        fetch_artifacts_url = []

        for artifact in self.image['artifacts']:
            if isinstance(artifact, _PlainResource) and \
               config.get('common', 'redhat'):
                fetch_artifacts_url.append({'md5': artifact['md5'],
                                            'url': get_brew_url(artifact['md5']),
                                            'target': os.path.join(artifact['target'])})
                artifact['target'] = os.path.join('artifacts', artifact['target'])
            else:
                artifact.copy(target_dir)

        if fetch_artifacts_url:
            with open('target/image/fetch-artifacts-url.yaml', 'w') as _file:
                yaml.safe_dump(fetch_artifacts_url, _file, default_flow_style=False)

        logger.debug("Artifacts handled")
