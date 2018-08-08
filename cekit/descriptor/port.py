import yaml
from cekit.descriptor.base import Descriptor

port_schemas = [yaml.safe_load("""
map:
  value: {type: int, required: True}
  protocol: {type: str}
  service: {type: str}
  expose: {type: bool}
  description: {type: str}""")]


class Port(Descriptor):
    """Object representing Port descriptor.
    If 'name' is not present, its generated from 'value'

    args:
       descriptor - yaml object containing Port definition"""

    def __init__(self, descriptor):
        self.schemas = port_schemas
        super(Port, self).__init__(descriptor)
        if 'name' not in self._descriptor:
            self._descriptor['name'] = self._descriptor['value']
