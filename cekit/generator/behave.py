from typing import List

from cekit.cekit_types import PathType
from cekit.generator.base import Generator


class BehaveGenerator(Generator):
    def __init__(
        self,
        descriptor_path: PathType,
        target: PathType,
        container_file: str,
        overrides: List[str],
    ):
        super(BehaveGenerator, self).__init__(
            descriptor_path, target, container_file, overrides
        )

    def prepare_artifacts(self):
        pass
