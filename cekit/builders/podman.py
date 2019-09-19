import logging
import os
import subprocess

from cekit.builder import Builder
from cekit.errors import CekitError

LOGGER = logging.getLogger('cekit')


class PodmanBuilder(Builder):
    """This class represents podman builder in build mode."""

    def __init__(self, params):
        super(PodmanBuilder, self).__init__('podman', params)

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps['podman'] = {
            'package': 'podman',
            'executable': 'podman'
        }

        return deps

    def run(self):
        """Build container image using podman."""
        tags = self.params.tags
        cmd = ["/usr/bin/podman", "build"]

        if not tags:
            tags = self.generator.get_tags()

        if self.params.pull:
            cmd.append('--pull-always')

        if not self.params.no_squash:
            cmd.append('--squash')

        # Custom tags for the container image
        LOGGER.debug("Building image with tags: '{}'".format("', '".join(tags)))

        for tag in tags:
            cmd.extend(["-t", tag])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, 'image'))

        LOGGER.debug("Running Podman build: '{}'".format(" ".join(cmd)))

        try:
            subprocess.check_call(cmd)

            LOGGER.info("Image built and available under following tags: {}".format(", ".join(tags)))
        except:
            raise CekitError("Image build failed, see logs above.")
