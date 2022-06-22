import logging
import os

from cekit.builder import Builder
from cekit.tools import run_wrapper

LOGGER = logging.getLogger("cekit")


class BuildahBuilder(Builder):
    """This class represents buildah builder in build-using-dockerfile mode."""

    def __init__(self, params):
        super(BuildahBuilder, self).__init__("buildah", params)

    @staticmethod
    def dependencies(params=None):
        deps = {}

        deps["buildah"] = {"package": "buildah", "executable": "buildah"}

        return deps

    def run(self):
        """Build container image using buildah."""
        tags = self.params.tags
        cmd = ["/usr/bin/buildah", "build-using-dockerfile"]

        if not tags:
            tags = self.generator.get_tags()

        if not self.params.no_squash:
            cmd.append("--squash")

        if self.params.pull:
            cmd.append("--pull-always")

        if self.params.platform:
            cmd.append("--platform")
            cmd.append(self.params.platform)

        # Custom tags for the container image
        LOGGER.debug("Building image with tags: '{}'".format("', '".join(tags)))

        for tag in tags:
            cmd.extend(["-t", tag])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, "image"))

        run_wrapper(cmd, False, f"Could not run buildah {cmd}")

        LOGGER.info(
            "Image built and available under following tags: {}".format(", ".join(tags))
        )
