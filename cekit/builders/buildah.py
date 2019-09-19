import logging
import os
import subprocess

from cekit.builder import Builder
from cekit.errors import CekitError

LOGGER = logging.getLogger('cekit')


class BuildahBuilder(Builder):
    """This class represents buildah builder in build-using-dockerfile mode."""

    def __init__(self, params):
        super(BuildahBuilder, self).__init__('buildah', params)

    @staticmethod
    def dependencies(params=None):
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

        if not self.params.no_squash:
            cmd.append('--squash')

        if self.params.pull:
            cmd.append('--pull-always')

        # Custom tags for the container image
        LOGGER.debug("Building image with tags: '{}'".format("', '".join(tags)))

        for tag in tags:
            cmd.extend(["-t", tag])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, 'image'))

        LOGGER.debug("Running Buildah build: '{}'".format(" ".join(cmd)))

        try:
            subprocess.check_call(cmd)

            LOGGER.info("Image built and available under following tags: {}".format(", ".join(tags)))
        except:
            raise CekitError("Image build failed, see logs above.")
