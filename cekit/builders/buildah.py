import logging
from typing import List

from cekit.builders.oci_builder import OCIBuilder
from cekit.cekit_types import DependencyDefinition
from cekit.tools import locate_binary

LOGGER = logging.getLogger("cekit")


class BuildahBuilder(OCIBuilder):
    """This class represents buildah builder in build-using-dockerfile mode."""

    def __init__(self, params):
        super(BuildahBuilder, self).__init__("buildah", params)

    @staticmethod
    def dependencies(params=None) -> DependencyDefinition:
        deps = {}

        deps["buildah"] = {"package": "buildah", "executable": "buildah"}

        return deps

    def run(self) -> None:
        """Build container image using buildah."""
        cmd: List[str] = [locate_binary("buildah"), "build-using-dockerfile"]
        self.common_build("buildah", cmd)
