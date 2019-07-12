import logging
import os

import yaml

from cekit.config import Config
from cekit.descriptor.resource import _PlainResource
from cekit.generator.base import Generator
from cekit.tools import get_brew_url, copy_recursively

logger = logging.getLogger('cekit')
config = Config()


class OSBSGenerator(Generator):
    def __init__(self, descriptor_path, target, overrides):
        self._wipe = True
        super(OSBSGenerator, self).__init__(descriptor_path, target, overrides)

    def init(self):
        super(OSBSGenerator, self).init()

        self._prepare_container_yaml()

    def generate(self, builder):
        # If extra directory exists (by default named 'osbs_extra') next to
        # the image descriptor, copy it contents to the target directory.
        #
        # https://github.com/cekit/cekit/issues/394
        copy_recursively(
            os.path.join(os.path.dirname(self._descriptor_path), self.image.osbs.extra_dir),
            os.path.join(self.target, 'image')
        )

        super(OSBSGenerator, self).generate(builder)

    def _prepare_content_sets(self, content_sets):
        content_sets_f = os.path.join(self.target, 'image', 'content_sets.yml')

        if not os.path.exists(os.path.dirname(content_sets_f)):
            os.makedirs(os.path.dirname(content_sets_f))

        with open(content_sets_f, 'w') as _file:
            yaml.safe_dump(content_sets, _file, default_flow_style=False)

    def _prepare_container_yaml(self):
        container_f = os.path.join(self.target, 'image', 'container.yaml')
        container = self.image.get('osbs', {}).get('configuration', {}).get('container')

        if not container:
            return

        if not os.path.exists(os.path.dirname(container_f)):
            os.makedirs(os.path.dirname(container_f))

        with open(container_f, 'w') as _file:
            yaml.safe_dump(container, _file, default_flow_style=False)

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
        fetch_artifacts_url = []

        for artifact in self.image.all_artifacts:
            logger.info("Preparing artifact {}".format(artifact['name']))

            if isinstance(artifact, _PlainResource) and \
               config.get('common', 'redhat'):
                try:
                    fetch_artifacts_url.append({'md5': artifact['md5'],
                                                'url': get_brew_url(artifact['md5']),
                                                'target': os.path.join(artifact['target'])})
                    artifact['target'] = os.path.join('artifacts', artifact['target'])
                    logger.debug("Artifact added to fetch-artifacts-url.yaml")
                except:
                    logger.warning("Plain artifact {} could not be found in Brew, trying to handle it using lookaside cache".
                                   format(artifact['name']))
                    artifact.copy(target_dir)
                    # TODO: This is ugly, rewrite this!
                    artifact['lookaside'] = True

            else:
                artifact.copy(target_dir)

        if fetch_artifacts_url:
            with open(os.path.join(self.target, 'image', 'fetch-artifacts-url.yaml'), 'w') as _file:
                yaml.safe_dump(fetch_artifacts_url, _file, default_flow_style=False)

        logger.debug("Artifacts handled")
