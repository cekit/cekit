import os
import yaml

from concreate.descriptor import Descriptor


volume_schema = [yaml.safe_load("""
map:
  name: {type: str}
  path: {type: str, required: True}""")]


class Volume(Descriptor):
    """Object representing Volume.
    If 'name' is not present its generated as basename of 'path'

    Args:
      descriptor - yaml file containing volume object
    """
    def __init__(self, descriptor):
        self.schemas = volume_schema
        super(Volume, self).__init__(descriptor)
        if 'name' not in self.descriptor:
            self.descriptor['name'] = os.path.basename(self.descriptor['path'])
