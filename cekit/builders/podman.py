import logging
from typing import List

from cekit.builders.oci_builder import OCIBuilder
from cekit.cekit_types import DependencyDefinition
from cekit.tools import locate_binary

LOGGER = logging.getLogger("cekit")


class PodmanBuilder(OCIBuilder):
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

        cmd: List[str] = [locate_binary("podman"), "build"]
        self.common_build("podman", cmd)
