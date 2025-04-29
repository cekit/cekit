import yaml

from cekit.descriptor.base import Descriptor

arg_schemas = yaml.safe_load(
    """
map:
  name: {type: str, required: True}
  value: {type: str}
  example: {type: str}
  description: {type: str}"""
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

    @property
    def example(self) -> str:
        return self.get("example")

    @example.setter
    def example(self, value: str):
        self._descriptor["example"] = value

    @property
    def description(self) -> str:
        return self.get("description")

    @description.setter
    def description(self, value: str):
        self._descriptor["description"] = value
