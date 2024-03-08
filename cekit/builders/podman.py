import logging
import os
from typing import List

from cekit.builder import Builder
from cekit.cekit_types import DependencyDefinition
from cekit.tools import locate_binary, run_wrapper

LOGGER = logging.getLogger("cekit")


class PodmanBuilder(Builder):
    """This class represents podman builder in build mode."""

    def __init__(self, params):
        super(PodmanBuilder, self).__init__("podman", params)

    @staticmethod
    def dependencies(params=None) -> DependencyDefinition:
        deps = {}

        deps["podman"] = {"package": "podman", "executable": "podman"}

        return deps

    def run(self):
        """Build container image using podman."""

        tags: List[str] = self.params.tags
        cmd: List[str] = [locate_binary("podman"), "build"]
        args: List[str] = self.params.args

        if not tags:
            tags = self.generator.get_tags()

        if self.params.trace:
            cmd += ["--log-level", "debug"]

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

        if args:
            for arg in args:
                cmd.extend(["--build-arg=" + arg])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, "image"))

        run_wrapper(cmd, False, f"Could not run podman {cmd}")

        LOGGER.info(
            f"Image built and available under following tags: {', '.join(tags)}"
        )
