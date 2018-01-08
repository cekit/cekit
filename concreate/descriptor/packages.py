import yaml

from concreate.descriptor import Descriptor


packages_schema = [yaml.safe_load("""
map:
  repositories:
    seq:
      - {type: str}
  install:
    seq:
      - {type: str}""")]


class Packages(Descriptor):
    """Object representing Pakcages

    Args:
      descriptor - yaml containing Packages section
    """
    def __init__(self, descriptor):
        self.schemas = packages_schema
        super(Packages, self).__init__(descriptor)
