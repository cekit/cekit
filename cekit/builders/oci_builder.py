import logging
import os
from typing import List

from cekit.builder import Builder
from cekit.tools import run_wrapper

LOGGER = logging.getLogger("cekit")


class OCIBuilder(Builder):
    def common_build(self, build_type: str, cmd: List[str], tagging=True):
        tags: List[str] = self.params.tags
        args: List[str] = self.params.build_args
        generic_args: List[str] = self.params.build_flag

        if tagging and not tags:
            tags = self.generator.get_tags()

        if not self.params.no_squash:
            cmd.append("--squash")

        if self.params.trace:
            cmd += ["--log-level", "debug"]

        if self.params.pull:
            cmd.append("--pull-always")

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

        if generic_args:
            for arg in generic_args:
                cmd.extend([arg])

        LOGGER.info("Building container image...")

        cmd.append(os.path.join(self.target, "image"))

        capture: bool = False
        if LOGGER.isEnabledFor(logging.DEBUG):
            # Normally we'll just let output print to stdout/stderr. If verbose(debug) is enabled
            # then we'll capture it but log it as well. This is useful for tests verifying the output.
            capture = True
        result = run_wrapper(cmd, capture, f"Could not run {build_type} {cmd}")
        if result.stdout is not None:
            LOGGER.debug(result.stdout)
            LOGGER.debug("\n")

        LOGGER.info(
            f"Image built and available under following tags: {', '.join(tags)}"
        )
