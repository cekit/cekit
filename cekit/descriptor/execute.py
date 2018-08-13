import yaml

import cekit

from cekit.descriptor import Descriptor


execute_schemas = [yaml.safe_load("""
        map:
          name: {type: str}
          script: {type: str}
          user: {type: text}""")]

container_schemas = [yaml.safe_load("""
        seq:
          - {type: any}""")]


class Execute(Descriptor):
    def __init__(self, descriptor, module_name):
        self.schemas = execute_schemas
        super(Execute, self).__init__(descriptor)

        descriptor['directory'] = module_name

        if 'user' not in descriptor:
            descriptor['user'] = cekit.DEFAULT_USER

        descriptor['module_name'] = module_name

        if 'name' not in descriptor:
            descriptor['name'] = "%s/%s" % (module_name,
                                            descriptor['script'])
