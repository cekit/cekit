import yaml

from cekit.descriptor.base import Descriptor

arg_schemas = yaml.safe_load(
    """
map:
  name: {type: str, required: True}
  value: {type: str}
"""
)


class Arg(Descriptor):
    """Object representing arg descriptor.

    Args:
      descriptor - yaml object with Arg
    """

    def __init__(self, descriptor: dict):
        self.schema = arg_schemas
        super(Arg, self).__init__(descriptor)

    @property
    def name(self) -> str:
        return self.get("name")

    @name.setter
    def name(self, value: str):
        self._descriptor["name"] = value

    @property
    def value(self) -> str:
        return self.get("value")

    @value.setter
    def value(self, value: str):
        self._descriptor["value"] = value
