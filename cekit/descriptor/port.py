from typing import Any

import yaml

from cekit.descriptor.base import Descriptor

port_schemas = yaml.safe_load(
    """
map:
  value: {type: int, required: True}
  protocol: {type: str}
  service: {type: str}
  expose: {type: bool}
  description: {type: str}"""
)


class Port(Descriptor):
    """Object representing Port descriptor.
    If 'name' is not present, its generated from 'value'

    args:
       descriptor - yaml object containing Port definition"""

    def __init__(self, descriptor: Any):
        self.schema = port_schemas
        super(Port, self).__init__(descriptor)
        if "name" not in self._descriptor:
            # TODO: Name probably has to be a string...
            self._descriptor["name"] = self._descriptor["value"]

    @property
    def value(self) -> int:
        return self.get("value")

    @value.setter
    def value(self, value: int):
        self._descriptor["value"] = value

    @property
    def protocol(self) -> str:
        return self.get("protocol")

    @protocol.setter
    def protocol(self, value: str):
        self._descriptor["protocol"] = value

    @property
    def service(self) -> str:
        return self.get("service")

    @service.setter
    def service(self, value: str):
        self._descriptor["service"] = value

    @property
    def expose(self) -> bool:
        return self.get("expose")

    @expose.setter
    def expose(self, value: bool):
        self._descriptor["expose"] = value

    @property
    def description(self) -> str:
        return self.get("description")

    @description.setter
    def description(self, value: str):
        self._descriptor["description"] = value
