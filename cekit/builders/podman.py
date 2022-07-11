import logging
import os

from cekit.builder import Builder
from cekit.tools import run_wrapper

LOGGER = logging.getLogger("cekit")


class PodmanBuilder(Builder):
    """This class represents podman builder in build mode."""

    def __init__(self, params):
        super(PodmanBuilder, self).__init__("podman", params)

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps["podman"] = {"package": "podman", "executable": "podman"}

        return deps

    def run(self):
        """Build container image using podman."""
        tags = self.params.tags
        cmd = ["/usr/bin/podman", "build"]

        if not tags:
            tags = self.generator.get_tags()

        if self.params.pull:
            cmd.append("--pull-always")

        if not self.params.no_squash:
            cmd.append("--squash")

        if self.params.platform:
            cmd.append("--platform")
            cmd.append(self.params.platform)

        # Custom tags for the container image
        LOGGER.debug("Building image with tags: '{}'".format("', '".join(tags)))

        for tag in tags:
            cmd.extend(["-t", tag])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, "image"))

        run_wrapper(cmd, False, f"Could not run podman {cmd}")

        LOGGER.info(
            "Image built and available under following tags: {}".format(", ".join(tags))
        )
