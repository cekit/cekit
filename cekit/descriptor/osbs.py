import yaml

from cekit.descriptor import Descriptor


osbs_schema = [yaml.safe_load("""
map:
  repository:
    map:
      name: {type: str}
      branch: {type: str}""")]


class Osbs(Descriptor):
    """Object Representing OSBS configuration

    Args:
      descriptor - yaml containing Osbs object
    """
    def __init__(self, descriptor):
        self.schemas = osbs_schema
        super(Osbs, self).__init__(descriptor)
