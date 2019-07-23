import logging
import yaml

import cekit
from cekit.descriptor import Descriptor

execute_schemas = yaml.safe_load("""
        map:
          name: {type: str}
          script: {type: str}
          user: {type: text}""")

container_schemas = yaml.safe_load("""
        seq:
          - {type: any}""")

logger = logging.getLogger('cekit')


class Execute(Descriptor):
    def __init__(self, descriptor, module_name):
        self.schema = execute_schemas
        super(Execute, self).__init__(descriptor)

        descriptor['directory'] = module_name
        descriptor['module_name'] = module_name

        if 'name' not in descriptor:
            # Generated name
            descriptor['name'] = "{}/{}".format(module_name, descriptor['script'])

            logger.debug("No value found for 'name' key in the execute section of the '{}' module; using auto-generated value: '{}'".format(
                module_name, descriptor['name']))

    @property
    def name(self):
        return self.get('name')

    @name.setter
    def name(self, value):
        self._descriptor['name'] = value

    @property
    def script(self):
        return self.get('script')

    @script.setter
    def script(self, value):
        self._descriptor['script'] = value

    @property
    def user(self):
        return self.get('user', cekit.DEFAULT_USER)

    @user.setter
    def user(self, value):
        self._descriptor['user'] = value
