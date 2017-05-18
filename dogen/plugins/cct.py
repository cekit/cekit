import logging
import os
import yaml
import requests
import shutil
import sys

from zipfile import ZipFile
from dogen.plugin import Plugin


class CCT(Plugin):
    @staticmethod
    def info():
        return "cct", "Support for configuring images via CCT"

    def __init__(self, dogen, args):
        super(CCT, self).__init__(dogen, args)

    def extend_schema(self, parent_schema):
        """
        Read in a schema definition for our part of the config and hook it
        into the parent schema at the cct: top-level key.
        """
        schema_path = os.path.join(self.dogen.pwd, "schema", "cct_schema.yaml")
        schema = {}
        with open(schema_path, 'r') as fh:
            schema = yaml.safe_load(fh)

        parent_schema['map']['cct'] = schema

    def setup_cct(self, version):
        cctdist = '%s/.dogen/plugin/cct/%s/%s.zip' % (os.path.expanduser('~'), version, version)
        cct_runtime = '%s/.dogen/plugin/cct/%s/cct.zip' % (os.path.expanduser('~'), version)
        if version == 'master':
            # we dont care if it doesnt exist - so we ignore errors here
            shutil.rmtree('%s/.dogen/plugin/cct/%s/' % (os.path.expanduser('~'), version), ignore_errors=True)
        elif os.path.exists(cctdist):
            return cct_runtime

        os.makedirs(os.path.dirname(cctdist))

        ccturl = 'https://github.com/containers-tools/cct/archive/%s.zip' % version
        with open(cctdist, 'wb') as f:
            f.write(requests.get(ccturl, verify=self.dogen.ssl_verify).content)

        ZipFile(cctdist).extractall(os.path.dirname(cctdist))

        content_root = os.path.join(os.path.dirname(cctdist), 'cct-%s' % version)
        with ZipFile(cct_runtime, "w") as zf:
            zf.write(os.path.join(content_root, '__main__.py'), '__main__.py')
            for root, directory, files in os.walk(os.path.join(content_root, 'cct')):
                for f in files:
                    arc_file = os.path.join(root, f)
                    zf.write(arc_file, arc_file[len(content_root):])

        return cct_runtime

    def prepare(self, cfg):
        """
        create cct changes yaml file for image.yaml template decscriptor
        it require cct aware template.jinja file
        """
        # check if cct plugin has any steps to perform (prevent it from raising ugly exceptions)
        if 'cct' not in cfg:
            self.log.debug("No cct key in image.yaml - nothing to do")
            return

        version = cfg['cct']['version'] if 'version' in cfg['cct'] else 'master'

        cct_runtime = self.setup_cct(version)

        sys.path.append(cct_runtime)
        # check if CCT is installed - complain otherwise
        # we are delaying import because CCT Plugin is not mandatory
        try:
            from cct.cli.main import CCT_CLI
        except ImportError:
            raise Exception("CCT was not set succesfully up!")

        cfg['cct']['run'] = ['cct.yaml']

        cct_dir = os.path.join(self.output, "cct")

        if not os.path.exists(cct_dir):
            os.makedirs(cct_dir)

        shutil.copy(cct_runtime, cct_dir)

        target_modules_dir = os.path.join(cct_dir, 'modules')
        if os.path.exists(target_modules_dir):
            shutil.rmtree(target_modules_dir)
            self.log.debug('Removed existing modules directory: %s' % target_modules_dir)

        os.makedirs(target_modules_dir)

        cfg_file = os.path.join(cct_dir, "cct.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct']['configure'], f)

        # copy cct modules from
        modules_dir = os.path.join(os.path.dirname(self.descriptor), 'cct', 'modules')
        if os.path.exists(modules_dir):
            modules = filter(lambda x: os.path.isdir(os.path.join(modules_dir, x)), os.listdir(modules_dir))
            for module in modules:
                target_module = os.path.join(target_modules_dir, module)
                shutil.copytree(os.path.join(modules_dir, module), target_module)
                self.log.info("Copied module %s to %s" % (module, target_module))

        # setup cct to same logging level as dogen
        cct_logger = logging.getLogger("cct")
        cct_logger.setLevel(self.log.getEffectiveLevel())

        cct = CCT_CLI()
        cfg['artifacts'] = cct.fetch_artifacts([cfg_file], target_modules_dir, self.output)

        self.log.info("CCT plugin downloaded artifacts")

        if 'runtime' in cfg['cct']:
            cfg['entrypoint'] = ['/usr/bin/cct']
            self.runtime_changes(cfg)
            cfg['entrypoint'].append(cfg['cct']['runtime_changes'])
            cfg['entrypoint'].append("-c")

        if 'user' not in cfg['cct']:
            cfg['cct']['user'] = 'root'

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
            yaml.dump(cfg['cct']['runtime'], f)

        # adjust cfg object so caller adds the above to ENTRYPOINT
        if 'runtime_changes' not in cfg['cct']:
            cfg['cct']['runtime_changes'] = "/tmp/cct/cctruntime.yaml"
