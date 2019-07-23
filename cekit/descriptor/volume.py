import logging
import os

import yaml

from cekit.descriptor import Descriptor

logger = logging.getLogger('cekit')

volume_schema = yaml.safe_load("""
map:
  name: {type: str}
  path: {type: str, required: True}""")


class Volume(Descriptor):
    """Object representing Volume.
    If 'name' is not present its generated as basename of 'path'

    Args:
      descriptor - yaml file containing volume object
    """

    def __init__(self, descriptor):
        self.schema = volume_schema
        super(Volume, self).__init__(descriptor)
        if 'name' not in self._descriptor:
            logger.warning("No value found for 'name' in 'volume'; using auto-generated value of '{}'".
                           format(os.path.basename(self._descriptor['path'])))
            self._descriptor['name'] = os.path.basename(self._descriptor['path'])
