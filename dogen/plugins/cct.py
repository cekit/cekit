import os
import yaml
import subprocess
import shutil

from dogen.plugin import Plugin


class CCT(Plugin):
    @staticmethod
    def info():
        return "cct", "Support for configuring images via cct"

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

    def prepare(self, cfg):
        """
        create cct changes yaml file for image.yaml template decscriptor
        it require cct aware template.jinja file
        """
        # check if cct plugin has any steps to perform (prevent it from raising ugly exceptions)
        if 'cct' not in cfg:
            self.log.debug("No cct key in image.yaml - nothing to do")
            return

        if os.path.exists(self.output + '/cct/'):
            shutil.rmtree(self.output + '/cct/')

        cfg['cct']['run'] = ['cct.yaml']

        cfg_file_dir = os.path.join(self.output, "cct")
        if not os.path.exists(cfg_file_dir):
            os.makedirs(cfg_file_dir)

        cfg_file = os.path.join(cfg_file_dir, "cct.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct']['configure'], f)

        # run cct with cfg file
        try:
            cmd = ['cct', '--modules-dir', cfg_file_dir, '-v', '--fetch-only', cfg_file]
            self.log.info("Executing %s" % " ".join(cmd))
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            self.log.info("CCT plugin downloaded artifacts")
            self.log.debug(out)
        except subprocess.CalledProcessError as e:
            self.log.error("Cannot download artifacts %s" % e.output)
            raise e

        if 'runtime' in cfg['cct']:
            self.runtime_changes(cfg)

        if 'user' not in cfg['cct']:
            cfg['cct']['user'] = 'root'

    def runtime_changes(self, cfg):
        """
        Handle configuring CCT for runtime use.

        User may supply a /cct/runtime key which will be written out as
        instructions for cct to execute at runtime.
        """

        # write out a cctruntime.yaml file from the /cct/runtime_changes key
        cfg_file_dir = os.path.join(self.output, "cct")
        if not os.path.exists(cfg_file_dir):
            os.makedirs(cfg_file_dir)
        cfg_file = os.path.join(cfg_file_dir, "cctruntime.yaml")
        with open(cfg_file, 'w') as f:
            yaml.dump(cfg['cct']['runtime'], f)

        # adjust cfg object so template adds the above to ENTRYPOINT
        if 'runtime_changes' not in cfg['cct']:
            cfg['cct']['runtime_changes'] = "/tmp/cct/cctruntime.yaml"
