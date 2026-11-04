import yaml
from cekit.descriptor import Descriptor

konflux_schema = yaml.safe_load(
"""
map:
  repository: {type: any}
  rpms.in.yaml: {type: any}
""")

repository_schema = yaml.safe_load("""
    map:
      uri: {type: str}
      ref: {type: str}
""")

class Konflux(Descriptor):
    """
    Object representing Konflux configuration

    Args:
      descriptor: dictionary object containing Konflux configuration
      path: path to descriptor file
    """

    def __init__(self, descriptor, path):
        self.schema = konflux_schema
        self.descriptor_path = path
        super(Konflux, self).__init__(descriptor)

        self["repository"] = Repository(
            self._descriptor.get("repository", {}),
            self.descriptor_path
        )

class Repository(Descriptor):
    def __init__(self, descriptor, descriptor_path):
        self.schema = repository_schema
        self.descriptor_path = descriptor_path
        super(Repository, self).__init__(descriptor)
