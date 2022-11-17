from typing import List

from cekit.generator.base import Generator
from cekit.types import PathType


class BehaveGenerator(Generator):
    def __init__(
        self, descriptor_path: PathType, target: PathType, overrides: List[str]
    ):
        super(BehaveGenerator, self).__init__(descriptor_path, target, overrides)

    def prepare_artifacts(self):
        pass
