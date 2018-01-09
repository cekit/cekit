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
      - {type: any}""")]

install_schema = [yaml.safe_load("""
map:
  name: {type: str, required: True}
  version: {type: str}""")]


class Modules(Descriptor):
    def __init__(self, descriptor):
        self.schemas = modules_schema
        super(Modules, self).__init__(descriptor)
        self._descriptor['repositories'] = [concreate.resource.Resource.new(r)
                                           for r in self._descriptor.get('repositories', [])]
        self._descriptor['install'] = [Install(x) for x in self._descriptor.get('install', [])]


class Install(Descriptor):
    def __init__(self, descriptor):
        self.schemas = install_schema
        super(Install, self).__init__(descriptor)
