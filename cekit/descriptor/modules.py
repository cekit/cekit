import yaml

from cekit.descriptor import Descriptor, Resource


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
    def __init__(self, descriptor, path):
        self.schemas = modules_schema
        super(Modules, self).__init__(descriptor)
        self._descriptor['repositories'] = [Resource(r, directory=path)
                                            for r in self._descriptor.get('repositories', [])]
        self._descriptor['install'] = [Install(x) for x in self._descriptor.get('install', [])]


class Install(Descriptor):
    def __init__(self, descriptor):
        self.schemas = install_schema
        super(Install, self).__init__(descriptor)
