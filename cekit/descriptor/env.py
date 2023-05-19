from typing import Any

import yaml

from cekit.descriptor import Descriptor

env_schema = yaml.safe_load(
    """
type: map
allowempty: True
mapping:
  name: {type: str, required: True}
  value: {type: any}
  example: {type: any}
  description: {type: str}"""
)


class Env(Descriptor):
    """Object representing Env variable

    Args:
      descriptor - yaml object containing Env variable
    """

    def __init__(self, descriptor):
        self.schema = env_schema
        super(Env, self).__init__(descriptor)

    @property
    def name(self) -> str:
        return self.get("name")

    @name.setter
    def name(self, value: str):
        self._descriptor["name"] = value

    @property
    def value(self) -> Any:
        # TODO: These should be string, need to update the schema.
        return self.get("value")

    @value.setter
    def value(self, value: Any):
        self._descriptor["value"] = value

    @property
    def example(self) -> Any:
        # TODO: These should be string, need to update the schema.
        return self.get("example")

    @example.setter
    def example(self, value: Any):
        self._descriptor["example"] = value

    @property
    def description(self) -> str:
        return self.get("description")

    @description.setter
    def description(self, value: str):
        self._descriptor["description"] = value
