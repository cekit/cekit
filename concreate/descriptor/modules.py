import yaml

import concreate

from concreate.descriptor import Descriptor


modules_schema = [yaml.safe_load("""
map:
  repositories:
    seq:
      - {type: any}
  install:
    seq:
      - map:
          name: {type: str, required: True}
          version: {type: str}""")]


class Modules(Descriptor):
    def __init__(self, descriptor):
        self.schemas = modules_schema
        super(Modules, self).__init__(descriptor)
        self.descriptor['repositories'] = [concreate.resource.Resource.new(r)
                                           for r in self.descriptor.get('repositories', [])]
