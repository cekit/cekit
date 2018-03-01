import yaml

from cekit.descriptor import Descriptor


env_schema = [yaml.safe_load("""
map:
  name: {type: str, required: True}
  value: {type: any}
  example: {type: any}
  description: {type: str}""")]


class Env(Descriptor):
    """Object representing Env variable

    Args:
      descriptor - yaml object containing Env variable
    """
    def __init__(self, descriptor):
        self.schemas = env_schema
        super(Env, self).__init__(descriptor)
