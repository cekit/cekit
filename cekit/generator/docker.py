import logging
import os

from cekit.config import Config
from cekit.generator.base import Generator

logger = logging.getLogger('cekit')
config = Config()


class DockerGenerator(Generator):

    def __init__(self, descriptor_path, target, overrides):
        super(DockerGenerator, self).__init__(descriptor_path, target, overrides)
        self._fetch_repos = True

    def _prepare_repository_rpm(self, repo):
        # no special handling is needed here, everything is in template
        pass

    def prepare_artifacts(self):
        """Goes through artifacts section of image descriptor
        and fetches all of them
        """

        logger.info("Handling artifacts for docker...")
        target_dir = os.path.join(self.target, 'image')

        for image in self.images:
            for artifact in image.all_artifacts:
                artifact.copy(target_dir)

        logger.debug("Artifacts handled")
