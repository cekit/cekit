import logging

import yaml

import cekit
from cekit.descriptor import Descriptor

execute_schemas = yaml.safe_load(
    """
        map:
          name: {type: str}
          script: {type: str}
          user: {type: text}"""
)

logger = logging.getLogger("cekit")


class Execute(Descriptor):
    def __init__(self, descriptor, module_name):
        self.schema = execute_schemas
        super(Execute, self).__init__(descriptor)

        descriptor["directory"] = module_name
        descriptor["module_name"] = module_name

        if "name" not in descriptor:
            descriptor["name"] = f"{module_name}/{descriptor['script']}"

    @property
    def name(self) -> str:
        return self.get("name")

    @name.setter
    def name(self, value: str):
        self._descriptor["name"] = value

    @property
    def script(self) -> str:
        return self.get("script")

    @script.setter
    def script(self, value: str):
        self._descriptor["script"] = value

    @property
    def user(self) -> str:
        return self.get("user", cekit.DEFAULT_USER)

    @user.setter
    def user(self, value: str):
        self._descriptor["user"] = value
