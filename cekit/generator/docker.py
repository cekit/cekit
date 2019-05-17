import logging
import os

from cekit.config import Config
from cekit.errors import CekitError
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
        if not self.image.all_artifacts:
            logger.debug("No artifacts to fetch")
            return

        logger.info("Handling artifacts...")
        target_dir = os.path.join(self.target, 'image')

        for artifact in self.image.all_artifacts:
            artifact.copy(target_dir)

        logger.debug("Artifacts handled")
