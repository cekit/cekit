from typing import List

from cekit.descriptor import Execute, Image
from cekit.descriptor.image import get_image_schema

overrides_schema = get_image_schema()
overrides_schema["map"]["execute"] = {"type": "any"}
overrides_schema["map"]["build_images"] = {"type": "any"}


class Module(Image):
    """Represents a module.

    Constructor arguments:
    descriptor_path: A path to module descriptor file.
    """

    def __init__(self, descriptor, path, artifact_dir):
        self._artifact_dir = artifact_dir
        self.path: str = path
        self.schema = overrides_schema.copy()
        # calling Descriptor constructor only here (we don't want Image() to mess with schema)
        super(Image, self).__init__(descriptor)
        self.skip_merging = ["description", "version", "name", "release", "help"]

        self._prepare()
        self.name: str = self._descriptor["name"]
        self._descriptor["execute"] = [
            Execute(x, self.name) for x in self._descriptor.get("execute", [])
        ]
        self._descriptor["build_images"] = [
            Image(i, self.path) for i in self._descriptor.get("build_images", [])
        ]

    @property
    def execute(self) -> List[Execute]:
        return self.get("execute")

    def build_images(self) -> List[Image]:
        return self.get("build_images")
