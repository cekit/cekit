import logging
import os
import yaml
import requests
import shutil
import sys

from dogen.plugin import Plugin


class CCT(Plugin):
    @staticmethod
    def info():
        return "cct", "Support for configuring images via CCT"

    def __init__(self, dogen, args):
        super(CCT, self).__init__(dogen, args)

    def setup_cct(self, version):
        cctdist = '%s/.dogen/plugin/cct/%s/cct.zip' % (os.path.expanduser('~'), version)
        if version == 'master':
            # we dont care if it doesnt exist - so we ignore errors here
            shutil.rmtree('%s/.dogen/plugin/cct/%s/' % (os.path.expanduser('~'), version), ignore_errors=True)
        elif os.path.exists(cctdist):
            return cctdist

        os.makedirs(os.path.dirname(cctdist))
        ccturl = 'https://github.com/containers-tools/cct/releases/download/%s/cct.zip' % version

        with open(cctdist, 'wb') as f:
            req = requests.get(ccturl, verify=self.dogen.ssl_verify)
            if req.status_code != 200:
                raise Exception("CCT cannot be downloaded from url:'%s' , status:'%s'" % (ccturl, req.status_code))
            f.write(req.content)

        return cctdist

    def get_cct_plugin(self, cfg):
        if 'dogen' not in cfg:
            cfg['dogen'] = {}
        if 'plugins' not in cfg['dogen']:
            cfg['dogen']['plugins'] = {}
        if 'cct' not in cfg['dogen']['plugins']:
            cfg['dogen']['plugins']['cct'] = {}
        return cfg['dogen']['plugins']['cct']

    def before_sources(self, cfg):
        """
        create cct changes yaml file for image.yaml template decscriptor
        it require cct aware template.jinja file
        """
        # check if cct plugin has any steps to perform (prevent it from raising ugly exceptions)
        if 'cct' not in cfg:
            self.log.debug("No cct key in image.yaml - nothing to do")
            return

        cct_config = self.get_cct_plugin(cfg)

        version = '0.4.1'
        if 'version' in cct_config:
            version = cct_config['version']

        if 'user' not in cct_config:
            cct_config['user'] = 'root'

        if 'verbose' not in cct_config:
            cct_config['verbose'] = True

        cct_runtime = self.setup_cct(version)

        sys.path.append(cct_runtime)
        # check if CCT is installed - complain otherwise
        # we are delaying import because CCT Plugin is not mandatory
        try:
            from cct import setup_logging as cct_setup_logging
            from cct.cli.main import CCT_CLI
            from cct import cfg as cct_cfg
        except ImportError:
            raise Exception("CCT was not set succesfully up!")

        cct_dir = os.path.join(self.output, "cct")

        if not os.path.exists(cct_dir):
            os.makedirs(cct_dir)
        shutil.copy(cct_runtime, cct_dir)

        target_modules_dir = os.path.join(cct_dir, 'modules')
        if os.path.exists(target_modules_dir):
            shutil.rmtree(target_modules_dir)
            os.makedirs(target_modules_dir)

        cfg_file = os.path.join(cct_dir, "cct.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct'], f)

        local_modules_dir = os.path.join(os.path.dirname(self.descriptor), 'cct')

        if os.path.exists(local_modules_dir) and not self.args.dist_git_enable:
            for module in os.listdir(local_modules_dir):
                module_path = os.path.join(local_modules_dir, module)
                self.log.info("Using cached module '%s' from path '%s'" % (module, module_path))
                shutil.copytree(module_path, os.path.join(target_modules_dir, module))

        # setup cct to same logging level as dogen
        cct_setup_logging()
        cct_logger = logging.getLogger("cct")
        cct_logger.handlers = self.log.handlers
        cct_logger.setLevel(self.log.getEffectiveLevel())

        cct_cfg.dogen = True
        cct = CCT_CLI()

        cct.process_changes([cfg_file], target_modules_dir, self.output)

        cfg['sources'] += cct_cfg.artifacts
        self.log.info("CCT plugin reported artifacts to dogen")

        for root, dirs, _ in os.walk(target_modules_dir):
            for d in dirs:
                if d == '.git':
                    shutil.rmtree(os.path.join(root, d))

        if 'cct_runtime' in cfg:
            cfg['entrypoint'] = ['/usr/bin/cct']
            self.runtime_changes(cfg)
            cfg['entrypoint'].append(cfg['cct_runtime'])
            cfg['entrypoint'].append("-c")

        self.install_cct_requirements(cfg)

    def install_cct_requirements(self, cfg):
        """Ensure that CCT's Python module requirements are installed in the image."""
        if "packages" not in cfg:
            cfg["packages"] = []
        for pkg in ['PyYAML']:
            if pkg not in cfg["packages"]:
                self.log.debug("adding {} to packages list".format(pkg))
                cfg["packages"].append(pkg)

    def runtime_changes(self, cfg):
        """
        Handle configuring CCT for runtime use.

        User may supply a /cct/runtime key which will be written out as
        instructions for cct to execute at runtime.
        """

        # write out a cctruntime.yaml file from the /cct/runtime_changes key
        cct_dir = os.path.join(self.output, "cct")
        if not os.path.exists(cct_dir):
            os.makedirs(cct_dir)
        cfg_file = os.path.join(cct_dir, "cctruntime.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct_runtime'], f)

        # adjust cfg object so caller adds the above to ENTRYPOINT
        if 'runtime_changes' not in cfg['cct']:
            cfg['cct']['runtime_changes'] = "/tmp/cct/cctruntime.yaml"
