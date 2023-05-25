import configparser
import os
from typing import Any, Dict, Optional

import yaml

from cekit.cekit_types import PathType

default_work_dir = "~/.cekit"


class Config(object):
    """Represents Cekit configuration - behaves as Singleton"""

    cfg = {}

    @classmethod
    def configure(cls, config_path: PathType, cmdline_args: Dict[str, Any]) -> None:
        cls._load_cfg(config_path)
        cls._override_config(cmdline_args)

    @classmethod
    def _override_config(cls, cmdline_args: Dict[str, Any]) -> None:
        # Only allow command line overriding of these values if they are not the default value.
        if cmdline_args.get("redhat"):
            cls.cfg["common"]["redhat"] = cmdline_args.get("redhat")
        if (
            cmdline_args.get("work_dir")
            and cmdline_args.get("work_dir") != default_work_dir
        ):
            cls.cfg["common"]["work_dir"] = cmdline_args.get("work_dir")

    @classmethod
    def _load_cfg(cls, config_path: PathType) -> None:
        """Loads configuration from cekit config file

        params:
        config_path - path to a cekit config file (expanding user)
        """
        config_parser = configparser.ConfigParser()
        config_parser.read(os.path.expanduser(config_path))
        # TODO: Fix this reference to protected member of class we don't control!
        cls.cfg = config_parser._sections
        cls.cfg["common"] = cls.cfg.get("common", {})
        cls.cfg["common"]["work_dir"] = cls.cfg.get("common").get(
            "work_dir", default_work_dir
        )
        cls.cfg["common"]["redhat"] = yaml.safe_load(
            cls.cfg.get("common", {}).get("redhat", "False")
        )

    @classmethod
    def get(cls, *args) -> Optional[str]:
        """Returns key value located by path of *args,
        None if Key doesn't exists,

        Args:
          * args - Path of key in Cekit config

        Raises:
          KeyError if section is not available."""
        value = cls.cfg
        for arg in args:
            if arg not in value and arg != args[-1]:
                raise KeyError(
                    "'%s' section doesnt exists in Cekit configuration!"
                    % "/".join(args[:-1])
                )
            value = value.get(arg)
        return value
