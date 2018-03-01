import yaml

import cekit

from cekit.descriptor import Descriptor


execute_schema = [yaml.safe_load("""
        map:
          script: {type: str}
          user: {type: text}""")]


class Execute(Descriptor):
    def __init__(self, descriptor, directory):
        self.schemas = execute_schema

        super(Execute, self).__init__(descriptor)

        descriptor['directory'] = directory

        if 'user' not in descriptor:
            descriptor['user'] = cekit.DEFAULT_USER

        if 'name' not in descriptor:
            descriptor['name'] = "%s/%s" % (directory,
                                            descriptor['script'])
