import logging
import os
import subprocess

from cekit.builder import Builder
from cekit.errors import CekitError

LOGGER = logging.getLogger('cekit')


class BuildahBuilder(Builder):
    """This class represents buildah builder in build-using-dockerfile mode."""

    def __init__(self, common_params, params):
        super(BuildahBuilder, self).__init__('buildah', common_params, params)

    @staticmethod
    def dependencies():
        deps = {}

        deps['buildah'] = {
            'package': 'buildah',
            'executable': 'buildah'
        }

        return deps

    def run(self):
        """Build container image using buildah."""
        tags = self.params.tags
        cmd = ["/usr/bin/buildah", "build-using-dockerfile"]

        if not tags:
            tags = self.generator.get_tags()

        if self.params.pull:
            cmd.append('--pull-always')

        # Custom tags for the container image
        LOGGER.debug("Building image with tags: '%s'" %
                     "', '".join(tags))

        for tag in tags:
            cmd.extend(["-t", tag])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, 'image'))

        LOGGER.debug("Running Buildah build: '%s'" % " ".join(cmd))

        try:
            subprocess.check_call(cmd)

            LOGGER.info("Image built and available under following tags: %s"
                        % ", ".join(tags))
        except:
            raise CekitError("Image build failed, see logs above.")
