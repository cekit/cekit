import yaml

from cekit.descriptor.base import Descriptor

port_schemas = yaml.safe_load("""
map:
  value: {type: int, required: True}
  protocol: {type: str}
  service: {type: str}
  expose: {type: bool}
  description: {type: str}""")


class Port(Descriptor):
    """Object representing Port descriptor.
    If 'name' is not present, its generated from 'value'

    args:
       descriptor - yaml object containing Port definition"""

    def __init__(self, descriptor):
        self.schema = port_schemas
        super(Port, self).__init__(descriptor)
        if 'name' not in self._descriptor:
            self._descriptor['name'] = self._descriptor['value']

    @property
    def value(self):
        return self.get('value')

    @value.setter
    def value(self, value):
        self._descriptor['value'] = value

    @property
    def protocol(self):
        return self.get('protocol')

    @protocol.setter
    def protocol(self, value):
        self._descriptor['protocol'] = value

    @property
    def service(self):
        return self.get('service')

    @service.setter
    def service(self, value):
        self._descriptor['service'] = value

    @property
    def expose(self):
        return self.get('expose')

    @expose.setter
    def expose(self, value):
        self._descriptor['expose'] = value

    @property
    def description(self):
        return self.get('description')

    @description.setter
    def description(self, value):
        self._descriptor['description'] = value
