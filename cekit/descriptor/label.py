import yaml

from cekit.descriptor.base import Descriptor


label_schemas = [yaml.safe_load("""
map:
  name: {type: str, required: True}
  value: {type: str, required: True}
  description: {type: str}
""")]


class Label(Descriptor):
    """Object representing label descriptor.

    Args:
      descriptor - yaml object with Label
    """
    def __init__(self, descriptor):
        self.schemas = label_schemas
        super(Label, self).__init__(descriptor)
