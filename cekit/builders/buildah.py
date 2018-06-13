import logging
import subprocess
import os

from cekit.builder import Builder
from cekit.errors import CekitError


logger = logging.getLogger('cekit')


class BuildahBuilder(Builder):
    """This class representes buildah builder in build-using-dockerfile mode."""

    def __init__(self, build_engine, target, params={}):
        self._tags = params.get('tags')
        self._pull = params.get('pull', False)  # --pull-always
        super(BuildahBuilder, self).__init__(build_engine, target, params)

    def check_prerequisities(self):
        try:
            subprocess.check_output(['sudo', 'buildah', 'version'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            raise CekitError("Buildah build engine needs buildah"
                             " installed and configured, error: %s"
                             % ex.output)
        except Exception as ex:
            raise CekitError("Buildah build engine needs buildah installed and configured!", ex)

    def build(self):
        """Build container image using buildah."""
        tags = self._tags
        cmd = ["sudo", "buildah", "build-using-dockerfile"]

        if self._pull:
            cmd.append('--pull-always')

        # Custom tags for the container image
        logger.debug("Building image with tags: '%s'" %
                     "', '".join(tags))

        for tag in tags:
            cmd.extend(["-t", tag])

        logger.info("Building container image...")

        cmd.append(os.path.join(self.target, 'image'))

        logger.debug("Running Buildah build: '%s'" % " ".join(cmd))

        try:
            subprocess.check_call(cmd)

            logger.info("Image built and available under following tags: %s"
                        % ", ".join(tags))
        except:
            raise CekitError("Image build failed, see logs above.")
