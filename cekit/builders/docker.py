import logging
import subprocess
import os

from cekit.builder import Builder
from cekit.errors import CekitError


logger = logging.getLogger('cekit')


class DockerBuilder(Builder):
    """This class wraps docker build command to build and image"""

    def __init__(self, build_engine, target, params={}):
        self._tags = params.get('tags')
        self._pull = params.get('pull', False)
        super(DockerBuilder, self).__init__(build_engine, target, params)

    def check_prerequisities(self):
        try:
            subprocess.check_output(['docker', 'info'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            raise CekitError("Docker build engine needs docker installed and configured, error: %s"
                             % ex.output)
        except Exception as ex:
            raise CekitError("Docker build engine needs docker installed and configured!", ex)

    def build(self):
        """After the source siles are generated, the container image can be built.
        We're using Docker to build the image currently.
        """
        tags = self._tags
        cmd = ["docker", "build"]

        if self._pull:
            cmd.append('--pull')

        # Custom tags for the container image
        logger.debug("Building image with tags: '%s'" %
                     "', '".join(tags))

        for tag in tags:
            cmd.extend(["-t", tag])

        logger.info("Building container image...")

        cmd.append(os.path.join(self.target, 'image'))

        logger.debug("Running Docker build: '%s'" % " ".join(cmd))

        try:
            subprocess.check_call(cmd)

            logger.info("Image built and available under following tags: %s"
                        % ", ".join(tags))
        except:
            raise CekitError("Image build failed, see logs above.")
