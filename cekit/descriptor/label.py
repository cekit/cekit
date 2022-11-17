import yaml

from cekit.descriptor.base import Descriptor

label_schemas = yaml.safe_load(
    """
map:
  name: {type: str, required: True}
  value: {type: str, required: True}
  description: {type: str}
"""
)


class Label(Descriptor):
    """Object representing label descriptor.

    Args:
      descriptor - yaml object with Label
    """

    def __init__(self, descriptor: dict):
        self.schema = label_schemas
        super(Label, self).__init__(descriptor)

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
    def description(self) -> str:
        return self.get("description")

    @description.setter
    def description(self, value: str):
        self._descriptor["description"] = value
