import logging
import os

import yaml

from cekit.descriptor import Descriptor
from cekit.errors import CekitError

osbs_schema = yaml.safe_load(
    """
map:
  repository: {type: any}
  configuration: {type: any}
  koji_target: {type: str}
  extra_dir: {type: str}
  extra_dir_target: {type: str}

"""
)

configuration_schema = yaml.safe_load(
    """
    map:
      container: {type: any}
      container_file: {type: str}
      gating_file: {type: str}
"""
)

repository_schema = yaml.safe_load(
    """
    map:
      name: {type: str}
      branch: {type: str}
"""
)

logger = logging.getLogger("cekit")


class Osbs(Descriptor):
    """
    Object Representing OSBS configuration

    Args:
      descriptor: dictionary object containing OSBS configuration
      descriptor_path: path to descriptor file
    """

    def __init__(self, descriptor, descriptor_path):
        self.schema = osbs_schema
        self.descriptor_path = descriptor_path
        super(Osbs, self).__init__(descriptor)

        self["configuration"] = Configuration(
            self._descriptor.get("configuration", {}), self.descriptor_path
        )

        self["repository"] = Repository(
            self._descriptor.get("repository", {}), self.descriptor_path
        )

    def merge(self, descriptor):
        if not descriptor:
            return self
        for k2, v2 in descriptor.items():
            if v2:
                self[k2] = v2
        return self

    @property
    def name(self):
        return self.get("name")

    @name.setter
    def name(self, value):
        self._descriptor["name"] = value

    @property
    def branch(self):
        return self.get("branch")

    @branch.setter
    def branch(self, value):
        self._descriptor["branch"] = value

    @property
    def configuration(self):
        return self.get("configuration")

    @property
    def extra_dir(self):
        return self.get("extra_dir")

    @extra_dir.setter
    def extra_dir(self, value):
        self._descriptor["extra_dir"] = value

    @property
    def extra_dir_target(self):
        return self.get("extra_dir_target")

    @extra_dir_target.setter
    def extra_dir_target(self, value):
        self._descriptor["extra_dir_target"] = value

    @property
    def koji_target(self):
        return self.get("koji_target")

    @koji_target.setter
    def koji_target(self, value):
        self._descriptor["koji_target"] = value

    @property
    def repository(self):
        return self.get("repository")


class Configuration(Descriptor):
    """Internal object representing OSBS configuration subObject

    Args:
      descriptor - yaml containing OSBS configuration"""

    def __init__(self, descriptor, descriptor_path):
        self.schema = configuration_schema
        self.descriptor_path = descriptor_path
        super(Configuration, self).__init__(descriptor)

        self._process_osbs_config_files(yaml.safe_load, "container", "container_file")
        self._process_osbs_config_files(
            lambda file: file.read(), "gating", "gating_file"
        )

        remote_source = self.get("container", {}).get("remote_source", {})
        if remote_source:
            logger.debug("Cachito definition is {}".format(remote_source))

    def _process_osbs_config_files(self, loader, text, filename):
        if text in self and filename in self:
            raise CekitError(
                "You cannot specify %s and %s together!" % (text, filename)
            )

        if filename in self:
            path = os.path.join(self.descriptor_path, self[filename])
            if not os.path.exists(path):
                raise CekitError("'%s' file not found!" % path)
            with open(path, "r") as file_:
                self[text] = loader(file_)
            del self[filename]


class Repository(Descriptor):
    def __init__(self, descriptor, descriptor_path):
        self.schema = repository_schema
        self.descriptor_path = descriptor_path
        super(Repository, self).__init__(descriptor)
