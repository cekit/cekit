import os
import yaml

try:
    import ConfigParser as configparser
except:
    import configparser


class Config(object):
    """Represents Cekit configuration - behaves as Singleton"""
    cfg = {}

    def configure(self, config_path, cmdline_args):
        self._load_cfg(config_path)
        self._override_config(cmdline_args)

    def _override_config(self, cmdline_args):
        if isinstance(cmdline_args.get('redhat'), bool):
            Config.cfg['common']['redhat'] = cmdline_args.get('redhat')
        if cmdline_args.get('work_dir'):
            Config.cfg['common']['work_dir'] = cmdline_args.get('work_dir')
        if isinstance(cmdline_args.get('addhelp'), bool):
            Config.cfg['doc']['addhelp'] = cmdline_args.get('addhelp')

    def _load_cfg(self, config_path):
        """ Loads configuration from cekit config file

        params:
        config_path - path to a cekit config file (expanding user)
        """
        cp = configparser.ConfigParser()
        cp.read(os.path.expanduser(config_path))
        Config.cfg = cp._sections
        Config.cfg['common'] = Config.cfg.get('common', {})
        Config.cfg['common']['work_dir'] = Config.cfg.get('common').get('work_dir', '~/.cekit')
        Config.cfg['common']['redhat'] = yaml.safe_load(
            Config.cfg.get('common', {}).get('redhat', 'False'))

        Config.cfg['doc'] = Config.cfg.get('doc', {})
        Config.cfg['doc']['addhelp'] = yaml.safe_load(
            Config.cfg.get('doc').get('addhelp', 'False'))

    def get(self, *args):
        value = Config.cfg
        for arg in args:
            value = value.get(arg)
        return value
