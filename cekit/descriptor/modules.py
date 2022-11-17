from typing import Any, List

import yaml

from cekit.descriptor import Descriptor
from cekit.descriptor.resource import Resource, create_resource

modules_schema = yaml.safe_load(
    """
map:
  repositories:
    seq:
      - {type: any}
  install:
    seq:
      - {type: any}"""
)

install_schema = yaml.safe_load(
    """
map:
  name: {type: str, required: True}
  version: {type: str}"""
)


class Modules(Descriptor):
    def __init__(self, descriptor, path):
        self.schema = modules_schema
        super(Modules, self).__init__(descriptor)
        self._descriptor["repositories"] = [
            create_resource(r, directory=path)
            for r in self._descriptor.get("repositories", [])
        ]
        self._descriptor["install"] = [
            Install(x) for x in self._descriptor.get("install", [])
        ]

    @property
    def repositories(self) -> List[Resource]:
        return self.get("repositories")

    @property
    def install(self) -> List["Install"]:
        return self.get("install")


class Install(Descriptor):
    def __init__(self, descriptor):
        self.schema = install_schema
        super(Install, self).__init__(descriptor)

    @property
    def name(self) -> str:
        return self.get("name")

    @name.setter
    def name(self, value: str):
        self._descriptor["name"] = value

    @property
    def version(self) -> Any:
        # TODO: convert to string up front to simplify things.
        return self.get("version")

    @version.setter
    def version(self, value: Any):
        self._descriptor["version"] = value
