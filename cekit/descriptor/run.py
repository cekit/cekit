import yaml

from cekit.descriptor import Descriptor


run_schema = [yaml.safe_load("""
map:
  workdir: {type: str}
  user: {type: text}
  cmd:
    seq:
      - {type: str}
  entrypoint:
    seq:
      - {type: str} """)]


class Run(Descriptor):
    """Object representing Run configuration
    If 'name' is not present 'run' string is used.

    Args:
       descriptor - a yaml containing descriptor object
    """
    def __init__(self, descriptor):
        self.schemas = run_schema
        super(Run, self).__init__(descriptor)
        if 'name' not in self._descriptor:
            self._descriptor['name'] = 'run'
        self.skip_merging = ['cmd', 'entrypoint']

    def merge(self, descriptor):
        for k2, v2 in descriptor.items():
            if k2 not in self:
                self[k2] = v2
